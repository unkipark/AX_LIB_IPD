"""환경변수 기반 설정. 배포 시 .env 파일 하나만 고치면 됩니다."""
from __future__ import annotations

from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- 서버 ----------
    host: str = "0.0.0.0"
    port: int = 8000
    static_dir: Path = Path("./static")
    # 브라우저가 접속하는 주소. OIDC redirect_uri 를 만드는 데 씁니다.
    #   예) http://10.10.1.20:8000  또는  https://ax-lib.사내도메인
    public_base_url: str = "http://localhost:8000"
    # "하루 1회" 사용 기록과 현황판 월별 집계의 기준 시간대
    timezone: str = "Asia/Seoul"

    # ---------- DB ----------
    database_url: str = "postgresql+psycopg://axlib:axlib@localhost:5432/axlib"

    # ---------- 파일 저장소 ----------
    upload_dir: Path = Path("./data/uploads")
    max_upload_mb: int = 100

    # ---------- 세션 ----------
    # 운영에서는 반드시 긴 난수로 바꾸세요:  python -c "import secrets; print(secrets.token_urlsafe(48))"
    session_secret: str = "change-me"
    session_max_age_hours: int = 12
    # HTTPS 로 서비스하면 true. http://IP 접속이면 false 여야 쿠키가 붙습니다.
    session_cookie_secure: bool = False

    # ---------- 인증 ----------
    # local: 사번 + 비밀번호 (앱 자체 계정).  oidc: 사내 SSO.
    # local 로 운영하다 oidc 로 바꾸면, 같은 사번의 기존 계정에 SSO 로그인이 자동 연결됩니다.
    auth_mode: Literal["local", "oidc"] = "local"
    # local 모드에서 누구나 가입할 수 있는지. false 면 관리자만 계정을 만들 수 있습니다.
    local_signup: bool = True
    # 연속 로그인 실패 시 잠금 (횟수, 분)
    login_max_failures: int = 5
    login_lock_minutes: int = 10

    # ---------- 사내 SSO (OIDC) — auth_mode=oidc 일 때만 사용 ----------
    # discovery 문서 주소. 보통 <issuer>/.well-known/openid-configuration
    oidc_discovery_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: str = "openid profile email"
    # 사내 CA 로 서명된 IdP 인증서를 쓰면 CA 번들 경로를 넣으세요.
    oidc_ca_bundle: str = ""

    # IdP 가 내려주는 claim 이름 → 앱 사용자 필드 매핑. 점(.)으로 중첩 claim 도 지정 가능.
    oidc_claim_id: str = "sub"
    oidc_claim_emp_no: str = "employee_number"
    oidc_claim_name: str = "name"
    oidc_claim_email: str = "email"
    oidc_claim_department: str = "department"

    # ---------- AI 도우미 (탐색·추천 Agent) ----------
    # 사내 LLM 게이트웨이(Anthropic API 형식)에 붙은 Claude Code 를 서브프로세스로 실행합니다.
    agent_enabled: bool = False
    claude_bin: str = "claude"
    anthropic_base_url: str = ""
    anthropic_auth_token: str = ""
    anthropic_model: str = ""
    # 동시에 돌릴 수 있는 대화 수. 넘치면 대기열에서 기다립니다.
    agent_max_concurrent: int = 3
    # 한 번의 질문(도구 호출 포함)에 허용하는 최대 시간(초)
    agent_timeout_sec: int = 180
    # 대화별 작업 폴더와 Claude Code 세션 저장 위치
    agent_work_dir: Path = Path("./data/agent")
    # Claude Code 가 MCP 도구를 부를 때 쓰는 앱 내부 주소 (같은 서버/컨테이너 안)
    internal_base_url: str = "http://127.0.0.1:8000"

    # 관리자 지정. 로그인 시 사번(또는 OIDC id claim)이 목록에 있으면 admin 권한이 붙습니다.
    admin_ids: str = ""

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def admin_id_set(self) -> set[str]:
        return {s.strip() for s in self.admin_ids.split(",") if s.strip()}

    @property
    def oidc_redirect_uri(self) -> str:
        return self.public_base_url.rstrip("/") + "/api/auth/callback"


settings = Settings()
