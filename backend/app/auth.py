"""사내 SSO(OIDC) 로그인과 현재 사용자 의존성.

흐름: /api/auth/login → IdP 로그인 → /api/auth/callback → users 테이블 upsert →
세션 쿠키에 uid 저장. 이름·부서는 매 로그인마다 IdP 값으로 갱신되므로 조직 개편이
자동 반영됩니다.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User, utcnow
from .schemas import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth = OAuth()
_client_kwargs: dict[str, Any] = {"scope": settings.oidc_scopes}
if settings.oidc_ca_bundle:
    _client_kwargs["verify"] = settings.oidc_ca_bundle
oauth.register(
    name="sso",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    server_metadata_url=settings.oidc_discovery_url,
    client_kwargs=_client_kwargs,
)


def _claim(claims: dict[str, Any], path: str) -> str | None:
    """'org.department' 처럼 점으로 구분된 중첩 claim 도 읽습니다."""
    cur: Any = claims
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    if cur is None:
        return None
    return str(cur).strip() or None


def _safe_next(next_url: str | None) -> str:
    # 오픈 리다이렉트 방지: 같은 오리진의 경로만 허용합니다.
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def upsert_user(db: Session, claims: dict[str, Any]) -> User:
    external_id = _claim(claims, settings.oidc_claim_id)
    if not external_id:
        raise HTTPException(400, f"SSO 응답에 사용자 식별자({settings.oidc_claim_id})가 없습니다")

    emp_no = _claim(claims, settings.oidc_claim_emp_no)
    user = db.scalar(select(User).where(User.external_id == external_id))
    if user is None:
        user = User(external_id=external_id)
        db.add(user)

    user.emp_no = emp_no
    user.name = _claim(claims, settings.oidc_claim_name) or external_id
    user.email = _claim(claims, settings.oidc_claim_email)
    user.department = _claim(claims, settings.oidc_claim_department)
    user.last_login_at = utcnow()
    if settings.admin_id_set & {external_id, emp_no or ""}:
        user.role = "admin"
    elif user.role is None:
        user.role = "user"
    db.commit()
    return user


@router.get("/login")
async def login(request: Request, next: str | None = None):
    request.session["next"] = _safe_next(next)
    return await oauth.sso.authorize_redirect(request, settings.oidc_redirect_uri)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.sso.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(401, f"SSO 로그인에 실패했습니다: {e.error}") from e

    claims: dict[str, Any] = dict(token.get("userinfo") or {})
    # 부서 같은 확장 claim 은 id_token 이 아니라 userinfo 에만 담아주는 IdP 가 많습니다.
    try:
        claims.update(await oauth.sso.userinfo(token=token))
    except Exception:  # noqa: BLE001 — userinfo 엔드포인트가 없는 IdP 도 있습니다.
        pass

    user = upsert_user(db, claims)
    next_url = request.session.pop("next", "/")
    # id_token 은 세션에 넣지 않습니다. 쿠키 세션이라 claim 이 많은 토큰이면 4KB 를 넘겨
    # 브라우저가 쿠키를 버리고, 로그인이 무한 반복됩니다.
    request.session["uid"] = user.id
    return RedirectResponse(_safe_next(next_url))


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    try:
        metadata = await oauth.sso.load_server_metadata()
        end_session = metadata.get("end_session_endpoint")
    except Exception:  # noqa: BLE001
        end_session = None
    if end_session:
        params = {
            "client_id": settings.oidc_client_id,
            "post_logout_redirect_uri": settings.public_base_url.rstrip("/") + "/",
        }
        return RedirectResponse(f"{end_session}?{urlencode(params)}")
    return RedirectResponse("/")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if user is None:
        raise HTTPException(401, "로그인이 필요합니다")
    return user


me_router = APIRouter(prefix="/api", tags=["auth"])


@me_router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
