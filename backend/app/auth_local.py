"""local 모드 로그인: 사번 + 비밀번호.

로그인 ID 를 사번으로 받는 이유: 나중에 AUTH_MODE=oidc 로 바꾸면 SSO 의 사번 claim 으로
기존 계정을 찾아 연결하므로, 그동안 등록한 산출물과 사용 기록이 그대로 이어집니다.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import start_session
from .config import settings
from .db import get_db
from .models import User
from .passwords import hash_password, verify_password
from .schemas import LoginIn, SignupIn, UserOut

router = APIRouter(prefix="/api/auth/local", tags=["auth"])

# 연속 실패 잠금. 프로세스 메모리에 두므로 재시작하면 풀립니다(단일 프로세스 운영 기준).
_failures: dict[str, tuple[int, float]] = {}
# 없는 사번으로 로그인할 때도 해시 계산 시간을 맞춰, 응답 시간으로 계정 존재 여부가 드러나지 않게 합니다.
_DUMMY_HASH = hash_password("dummy-password")


def _check_lock(login_id: str) -> None:
    _, locked_until = _failures.get(login_id, (0, 0.0))
    remaining = locked_until - time.monotonic()
    if remaining > 0:
        raise HTTPException(429, f"로그인 실패가 많아 잠겼습니다. {int(remaining // 60) + 1}분 후 다시 시도하세요")


def _record_failure(login_id: str) -> None:
    count, _ = _failures.get(login_id, (0, 0.0))
    count += 1
    if count >= settings.login_max_failures:
        _failures[login_id] = (0, time.monotonic() + settings.login_lock_minutes * 60)
    else:
        _failures[login_id] = (count, 0.0)


def clear_lock(login_id: str) -> None:
    _failures.pop(login_id, None)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    _check_lock(body.login_id)
    user = db.scalar(select(User).where(User.login_id == body.login_id))
    if not verify_password(body.password, user.password_hash if user else _DUMMY_HASH) or user is None:
        _record_failure(body.login_id)
        raise HTTPException(401, "사번 또는 비밀번호가 올바르지 않습니다")
    if not user.is_active:
        raise HTTPException(403, "비활성화된 계정입니다. 관리자에게 문의하세요")
    clear_lock(body.login_id)
    start_session(request, db, user)
    return user


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn, request: Request, db: Session = Depends(get_db)):
    if not settings.local_signup:
        raise HTTPException(403, "가입이 막혀 있습니다. 관리자에게 계정 생성을 요청하세요")
    user = create_local_user(db, body)
    start_session(request, db, user)
    return user


def create_local_user(db: Session, body: SignupIn) -> User:
    exists = db.scalar(select(User).where((User.login_id == body.login_id) | (User.emp_no == body.login_id)))
    if exists:
        raise HTTPException(409, "이미 가입된 사번입니다")
    user = User(
        login_id=body.login_id, emp_no=body.login_id, password_hash=hash_password(body.password),
        name=body.name, department=body.department, email=body.email, role="user",
    )
    db.add(user)
    db.commit()
    return user
