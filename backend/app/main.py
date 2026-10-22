"""FastAPI 엔트리포인트.

빌드된 프론트엔드(static/)를 같은 오리진에서 서빙하므로 CORS 설정이 필요 없고,
세션 쿠키도 그대로 동작합니다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth
from .config import settings
from .routers import artifacts, dashboard

app = FastAPI(title="AX 산출물 라이브러리", version="0.1.0")

if settings.session_secret == "change-me":
    logging.getLogger("uvicorn.error").warning(
        "SESSION_SECRET 가 기본값입니다. 세션 위조를 막으려면 .env 에서 긴 난수로 바꾸세요."
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="axlib_session",
    max_age=settings.session_max_age_hours * 3600,
    same_site="lax",  # IdP 에서 돌아오는 GET 리다이렉트에 쿠키가 실려야 합니다.
    https_only=settings.session_cookie_secure,
)

app.include_router(auth.router)
app.include_router(auth.me_router)
app.include_router(artifacts.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------- 정적 파일 (빌드된 프론트엔드) ----------
_static = Path(settings.static_dir)
if _static.exists():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        candidate = (_static / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_static.resolve()):
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")


def main() -> None:
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
