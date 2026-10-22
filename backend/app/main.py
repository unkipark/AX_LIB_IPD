"""FastAPI 엔트리포인트.

빌드된 프론트엔드(static/)를 같은 오리진에서 서빙하므로 CORS 설정이 필요 없고,
세션 쿠키도 그대로 동작합니다.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth, mcp_server
from .config import settings
from .routers import admin, agent, artifacts, dashboard

# MCP 앱은 lifespan 전에 만들어 둬야 session_manager 가 준비됩니다.
_mcp_app = mcp_server.build_app()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp_server.mcp.session_manager.run():
        yield


app = FastAPI(title="AX 산출물 라이브러리", version="0.1.0", lifespan=lifespan)

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
if settings.auth_mode == "oidc":
    from . import auth_oidc

    app.include_router(auth_oidc.router)
else:
    from . import auth_local

    app.include_router(auth_local.router)
app.include_router(admin.router)
app.include_router(agent.router)
# AI 도우미(Claude Code)가 부르는 MCP 서버. 끝의 / 까지 포함한 /mcp/ 로 접속합니다.
app.mount("/mcp", _mcp_app)
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
