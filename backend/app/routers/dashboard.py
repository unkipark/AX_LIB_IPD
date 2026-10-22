"""현황판 집계. 부서 규모(수백~수천 건)에서는 한 번에 계산해도 충분히 빠릅니다."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import catalog
from ..auth import current_user
from ..config import settings
from ..db import get_db
from ..models import Artifact, ArtifactTool, UsageEvent, User
from .artifacts import NO_DEPARTMENT

router = APIRouter(prefix="/api", tags=["dashboard"])

MONTHS = 12


def _month_keys(now: datetime) -> list[str]:
    y, m = now.year, now.month
    keys = []
    for _ in range(MONTHS):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return keys[::-1]


def _breakdown(counter: Counter, labels: dict[str, str]) -> list[dict]:
    """catalog 순서를 유지하고, 0건인 항목도 그대로 둡니다(막대 위치가 매번 같도록)."""
    return [{"key": k, "label": v, "count": counter.get(k, 0)} for k, v in labels.items()]


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(current_user)):
    tz = settings.tz
    now = datetime.now(tz)
    months = _month_keys(now)

    artifacts = db.execute(
        select(Artifact.id, Artifact.title, Artifact.type, Artifact.status, Artifact.department,
               Artifact.owner_id, Artifact.time_saved_min, Artifact.created_at)
    ).all()
    by_id = {a.id: a for a in artifacts}

    used = db.execute(
        select(UsageEvent.artifact_id, UsageEvent.user_id, UsageEvent.created_at).where(UsageEvent.kind == "used")
    ).all()
    downloads = db.scalar(select(func.count()).select_from(UsageEvent).where(UsageEvent.kind == "download")) or 0
    tools = Counter(t for (t,) in db.execute(select(ArtifactTool.tool)).all())

    uses_per_artifact = Counter(u.artifact_id for u in used)
    saved_min_per_artifact = {
        aid: n * (by_id[aid].time_saved_min or 0) for aid, n in uses_per_artifact.items() if aid in by_id
    }

    created_per_month = Counter(a.created_at.astimezone(tz).strftime("%Y-%m") for a in artifacts)
    used_per_month = Counter(u.created_at.astimezone(tz).strftime("%Y-%m") for u in used)

    owners = Counter(a.owner_id for a in artifacts)
    owner_rows = {
        u.id: u for u in db.scalars(select(User).where(User.id.in_(owners.keys()))).all()
    } if owners else {}

    def artifact_ref(aid: int) -> dict:
        a = by_id[aid]
        return {"id": a.id, "title": a.title, "type": a.type, "status": a.status}

    return {
        "kpi": {
            "artifacts": len(artifacts),
            "deployed": sum(1 for a in artifacts if a.status == "deployed"),
            "contributors": len(owners),
            "uses": len(used),
            "users": len({u.user_id for u in used}),
            "downloads": downloads,
            "savedHours": round(sum(saved_min_per_artifact.values()) / 60, 1),
        },
        "byStatus": _breakdown(Counter(a.status for a in artifacts), catalog.STATUSES),
        "byType": _breakdown(Counter(a.type for a in artifacts), catalog.ARTIFACT_TYPES),
        "byTool": _breakdown(tools, catalog.AI_TOOLS),
        "byDepartment": [
            {"key": d or NO_DEPARTMENT, "label": d or "미지정", "count": n}
            for d, n in Counter(a.department for a in artifacts).most_common()
        ],
        "monthly": [
            {"month": m, "created": created_per_month.get(m, 0), "used": used_per_month.get(m, 0)} for m in months
        ],
        "topUsed": [
            {**artifact_ref(aid), "uses": n, "savedHours": round(saved_min_per_artifact.get(aid, 0) / 60, 1)}
            for aid, n in uses_per_artifact.most_common(5) if aid in by_id
        ],
        "topContributors": [
            {"id": uid, "name": owner_rows[uid].name, "department": owner_rows[uid].department, "count": n}
            for uid, n in owners.most_common(5) if uid in owner_rows
        ],
        "recent": [
            {**artifact_ref(a.id), "createdAt": a.created_at}
            for a in sorted(artifacts, key=lambda a: a.created_at, reverse=True)[:5]
        ],
    }
