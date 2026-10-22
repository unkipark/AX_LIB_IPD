"""산출물 CRUD · 첨부파일 · 사용 기록."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import catalog
from ..auth import current_user
from ..config import settings
from ..db import get_db
from ..models import Artifact, ArtifactFile, ArtifactTag, ArtifactTool, UsageEvent, User
from ..schemas import ArtifactDetail, ArtifactIn, ArtifactPage, ArtifactSummary, FileOut, OwnerOut

router = APIRouter(prefix="/api", tags=["artifacts"])


@router.get("/meta")
def get_meta():
    return catalog.meta()


# ---------- 헬퍼 ----------

def _today_start() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def _counts(db: Session, ids: list[int], kind: str) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(UsageEvent.artifact_id, func.count())
        .where(UsageEvent.artifact_id.in_(ids), UsageEvent.kind == kind)
        .group_by(UsageEvent.artifact_id)
    )
    return dict(rows.all())


def _summary(a: Artifact, use_count: int) -> ArtifactSummary:
    return ArtifactSummary(
        id=a.id, title=a.title, summary=a.summary, type=a.type, status=a.status,
        tools=[t.tool for t in a.tools], tags=[t.tag for t in a.tags],
        owner=OwnerOut.model_validate(a.owner), department=a.department,
        time_saved_min=a.time_saved_min, use_count=use_count, file_count=len(a.files),
        created_at=a.created_at, updated_at=a.updated_at,
    )


def _can_edit(a: Artifact, user: User) -> bool:
    return user.role == "admin" or a.owner_id == user.id


def _get(db: Session, artifact_id: int) -> Artifact:
    a = db.get(Artifact, artifact_id)
    if a is None:
        raise HTTPException(404, "산출물을 찾을 수 없습니다")
    return a


def _get_editable(db: Session, artifact_id: int, user: User) -> Artifact:
    a = _get(db, artifact_id)
    if not _can_edit(a, user):
        raise HTTPException(403, "등록자 또는 관리자만 수정할 수 있습니다")
    return a


def _apply(a: Artifact, body: ArtifactIn) -> None:
    for field in ("title", "summary", "description", "install_guide", "type", "status",
                  "process", "version", "repo_url", "time_saved_min"):
        setattr(a, field, getattr(body, field))
    a.tools = [ArtifactTool(tool=t) for t in body.tools]
    a.tags = [ArtifactTag(tag=t) for t in body.tags]


def _detail(db: Session, a: Artifact, user: User) -> ArtifactDetail:
    used_today = db.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.artifact_id == a.id, UsageEvent.user_id == user.id,
            UsageEvent.kind == "used", UsageEvent.created_at >= _today_start(),
        )
    )
    base = _summary(a, _counts(db, [a.id], "used").get(a.id, 0))
    return ArtifactDetail(
        **base.model_dump(),
        description=a.description, install_guide=a.install_guide, process=a.process,
        version=a.version, repo_url=a.repo_url,
        files=[FileOut(id=f.id, name=f.original_name, size=f.size, content_type=f.content_type,
                       created_at=f.created_at) for f in a.files],
        download_count=_counts(db, [a.id], "download").get(a.id, 0),
        used_by_me_today=bool(used_today), can_edit=_can_edit(a, user),
    )


# ---------- 산출물 ----------

@router.get("/artifacts", response_model=ArtifactPage)
def list_artifacts(
    q: str = "",
    type: str = "",
    status: str = "",
    tool: str = "",
    department: str = "",
    mine: bool = False,
    sort: Literal["recent", "popular", "title"] = "recent",
    page: int = 1,
    size: int = 24,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    page, size = max(page, 1), min(max(size, 1), 100)
    stmt = select(Artifact)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Artifact.title.ilike(like), Artifact.summary.ilike(like), Artifact.process.ilike(like),
            Artifact.id.in_(select(ArtifactTag.artifact_id).where(ArtifactTag.tag.ilike(like))),
        ))
    if type:
        stmt = stmt.where(Artifact.type == type)
    if status:
        stmt = stmt.where(Artifact.status == status)
    if tool:
        stmt = stmt.where(Artifact.id.in_(select(ArtifactTool.artifact_id).where(ArtifactTool.tool == tool)))
    if department:
        stmt = stmt.where(Artifact.department == department)
    if mine:
        stmt = stmt.where(Artifact.owner_id == user.id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    if sort == "popular":
        uses = (
            select(func.count()).where(UsageEvent.artifact_id == Artifact.id, UsageEvent.kind == "used")
            .correlate(Artifact).scalar_subquery()
        )
        stmt = stmt.order_by(uses.desc(), Artifact.updated_at.desc())
    elif sort == "title":
        stmt = stmt.order_by(Artifact.title)
    else:
        stmt = stmt.order_by(Artifact.updated_at.desc())

    stmt = stmt.options(
        selectinload(Artifact.owner), selectinload(Artifact.tools),
        selectinload(Artifact.tags), selectinload(Artifact.files),
    ).offset((page - 1) * size).limit(size)
    items = db.scalars(stmt).all()
    uses_by_id = _counts(db, [a.id for a in items], "used")
    return ArtifactPage(items=[_summary(a, uses_by_id.get(a.id, 0)) for a in items], total=total)


@router.post("/artifacts", response_model=ArtifactDetail, status_code=201)
def create_artifact(body: ArtifactIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = Artifact(owner_id=user.id, department=user.department)
    _apply(a, body)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _detail(db, a, user)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetail)
def get_artifact(artifact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _detail(db, _get(db, artifact_id), user)


@router.put("/artifacts/{artifact_id}", response_model=ArtifactDetail)
def update_artifact(
    artifact_id: int, body: ArtifactIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    a = _get_editable(db, artifact_id, user)
    _apply(a, body)
    db.commit()
    db.refresh(a)
    return _detail(db, a, user)


@router.delete("/artifacts/{artifact_id}", status_code=204)
def delete_artifact(artifact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _get_editable(db, artifact_id, user)
    db.delete(a)
    db.commit()
    shutil.rmtree(settings.upload_dir / str(artifact_id), ignore_errors=True)


# ---------- 사용 기록 ----------

@router.post("/artifacts/{artifact_id}/used")
def mark_used(artifact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """'써봤어요'. 같은 사람이 같은 날 여러 번 눌러도 1건만 남습니다."""
    a = _get(db, artifact_id)
    exists = db.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.artifact_id == a.id, UsageEvent.user_id == user.id,
            UsageEvent.kind == "used", UsageEvent.created_at >= _today_start(),
        )
    )
    if not exists:
        db.add(UsageEvent(artifact_id=a.id, user_id=user.id, kind="used"))
        db.commit()
    return {"useCount": _counts(db, [a.id], "used").get(a.id, 0)}


# ---------- 첨부파일 ----------

@router.post("/artifacts/{artifact_id}/files", response_model=FileOut, status_code=201)
def upload_file(
    artifact_id: int, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    a = _get_editable(db, artifact_id, user)
    folder = settings.upload_dir / str(a.id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = uuid.uuid4().hex
    dest = folder / stored_name
    limit = settings.max_upload_mb * 1024 * 1024
    written = 0
    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"파일은 {settings.max_upload_mb}MB 까지 올릴 수 있습니다")
            out.write(chunk)

    f = ArtifactFile(
        artifact_id=a.id, original_name=(file.filename or stored_name)[:300], stored_name=stored_name,
        size=written, content_type=file.content_type or "application/octet-stream", uploaded_by=user.id,
    )
    db.add(f)
    db.commit()
    return FileOut(id=f.id, name=f.original_name, size=f.size, content_type=f.content_type, created_at=f.created_at)


@router.get("/files/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = db.get(ArtifactFile, file_id)
    path = settings.upload_dir / str(f.artifact_id) / f.stored_name if f else None
    if f is None or path is None or not path.exists():
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    db.add(UsageEvent(artifact_id=f.artifact_id, user_id=user.id, kind="download"))
    db.commit()
    return FileResponse(path, media_type=f.content_type, filename=f.original_name)


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = db.get(ArtifactFile, file_id)
    if f is None:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    _get_editable(db, f.artifact_id, user)
    (settings.upload_dir / str(f.artifact_id) / f.stored_name).unlink(missing_ok=True)
    db.delete(f)
    db.commit()
