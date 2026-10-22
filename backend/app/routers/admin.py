"""관리자: 사용자 목록, 계정 생성, 권한·활성 상태 변경, 비밀번호 초기화."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..auth_local import clear_lock, create_local_user
from ..config import settings
from ..db import get_db
from ..models import Artifact, User
from ..passwords import hash_password, temp_password
from ..schemas import AdminUserOut, AdminUserUpdate, SignupIn

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _out(user: User, artifact_count: int) -> AdminUserOut:
    return AdminUserOut(
        id=user.id, login_id=user.login_id, emp_no=user.emp_no, name=user.name, email=user.email,
        department=user.department, role=user.role, is_active=user.is_active,
        last_login_at=user.last_login_at, artifact_count=artifact_count,
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    counts = dict(db.execute(select(Artifact.owner_id, func.count()).group_by(Artifact.owner_id)).all())
    users = db.scalars(select(User).order_by(User.department, User.name)).all()
    return [_out(u, counts.get(u.id, 0)) for u in users]


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(body: SignupIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """LOCAL_SIGNUP=false 로 운영할 때 관리자가 계정을 만들어 줍니다."""
    if settings.auth_mode != "local":
        raise HTTPException(400, "SSO 모드에서는 첫 로그인 때 계정이 자동으로 만들어집니다")
    return _out(create_local_user(db, body), 0)


@router.put("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int, body: AdminUserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")
    if user.id == admin.id and (body.role == "user" or body.is_active is False):
        raise HTTPException(400, "자기 자신의 관리자 권한이나 계정은 끌 수 없습니다")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    count = db.scalar(select(func.count()).select_from(Artifact).where(Artifact.owner_id == user.id)) or 0
    return _out(user, count)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """임시 비밀번호를 만들어 돌려줍니다. 사용자에게 전달하고, 로그인 후 바꾸도록 안내하세요."""
    if settings.auth_mode != "local":
        raise HTTPException(400, "SSO 모드에서는 비밀번호를 관리하지 않습니다")
    user = db.get(User, user_id)
    if user is None or not user.login_id:
        raise HTTPException(404, "비밀번호로 로그인하는 사용자가 아닙니다")
    password = temp_password()
    user.password_hash = hash_password(password)
    db.commit()
    clear_lock(user.login_id)
    return {"tempPassword": password}
