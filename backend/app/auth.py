"""인증 공통: 세션, 현재 사용자, 내 정보, 인증 방식 안내.

로그인 방식은 AUTH_MODE 로 고릅니다.
  local → auth_local.py (사번 + 비밀번호)
  oidc  → auth_oidc.py  (사내 SSO)
어느 쪽이든 로그인에 성공하면 세션 쿠키에 uid 하나만 저장합니다.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User, utcnow
from .passwords import hash_password, verify_password
from .schemas import PasswordChangeIn, ProfileIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
me_router = APIRouter(prefix="/api", tags=["auth"])


def safe_next(next_url: str | None) -> str:
    # 오픈 리다이렉트 방지: 같은 오리진의 경로만 허용합니다.
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def start_session(request: Request, db: Session, user: User) -> None:
    """로그인 성공 처리. ADMIN_IDS 에 있으면 관리자 권한을 붙입니다."""
    if settings.admin_id_set & {user.login_id or "", user.emp_no or "", user.external_id or ""}:
        user.role = "admin"
    elif not user.role:
        user.role = "user"
    user.last_login_at = utcnow()
    db.commit()
    request.session.clear()
    request.session["uid"] = user.id


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if user is None or not user.is_active:
        raise HTTPException(401, "로그인이 필요합니다")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "관리자만 사용할 수 있습니다")
    return user


def _require_local() -> None:
    if settings.auth_mode != "local":
        raise HTTPException(400, "SSO 로 로그인하는 환경에서는 사내 시스템에서 정보를 변경하세요")


@router.get("/config")
def auth_config(db: Session = Depends(get_db)):
    """로그인 전에 프론트엔드가 읽는 정보. 가입·내 정보 화면의 부서 자동완성 목록도 함께 줍니다.
    부서 표기가 사람마다 달라지면 현황판의 부서별 집계가 갈라지므로, 기존 표기를 고르도록 유도합니다."""
    departments: list[str] = []
    if settings.auth_mode == "local":
        departments = sorted(
            d for (d,) in db.execute(select(User.department).where(User.department.is_not(None)).distinct())
        )
    return {"mode": settings.auth_mode, "signup": settings.local_signup, "departments": departments}


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    if settings.auth_mode == "oidc":
        from .auth_oidc import end_session_url

        url = await end_session_url()
        if url:
            return RedirectResponse(url)
        return RedirectResponse("/")
    return RedirectResponse("/login")


@me_router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@me_router.put("/me", response_model=UserOut)
def update_me(body: ProfileIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """local 모드에서 본인 이름·부서·이메일 변경. 이미 등록한 산출물의 부서는 바뀌지 않습니다."""
    _require_local()
    user.name, user.department, user.email = body.name, body.department, body.email
    db.commit()
    return user


@me_router.put("/me/password", status_code=204)
def change_password(body: PasswordChangeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _require_local()
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "현재 비밀번호가 올바르지 않습니다")
    user.password_hash = hash_password(body.new_password)
    db.commit()
