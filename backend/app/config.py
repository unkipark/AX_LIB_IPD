"""환경변수 기반 설정. 배포 시 .env 파일 하나만 고치면 됩니다."""
from __future__ import annotations

from pathlib import Path

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

    # ---------- 사내 SSO (OIDC) ----------
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

    # 관리자 지정. 로그인 시 id claim 또는 사번이 목록에 있으면 admin 권한이 붙습니다.
    admin_ids: str = ""

    @property
    def admin_id_set(self) -> set[str]:
        return {s.strip() for s in self.admin_ids.split(",") if s.strip()}

    @property
    def oidc_redirect_uri(self) -> str:
        return self.public_base_url.rstrip("/") + "/api/auth/callback"


settings = Settings()
