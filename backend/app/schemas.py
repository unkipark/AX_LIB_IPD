"""API 입출력 모델. JSON 키는 프론트엔드 관례에 맞춰 camelCase 로 나갑니다."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from . import catalog


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UserOut(ApiModel):
    id: int
    login_id: str | None
    name: str
    email: str | None
    department: str | None
    emp_no: str | None
    role: str


# ---------- 인증 ----------

LOGIN_ID_PATTERN = r"^[A-Za-z0-9._-]{2,50}$"


def _blank_to_none(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


class LoginIn(ApiModel):
    login_id: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login_id")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ProfileIn(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("이름을 입력하세요")
        return v.strip()

    @field_validator("department", "email")
    @classmethod
    def _optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)


class SignupIn(ProfileIn):
    login_id: str = Field(pattern=LOGIN_ID_PATTERN, description="사번")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("login_id", mode="before")
    @classmethod
    def _strip_id(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class PasswordChangeIn(ApiModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserOut(ApiModel):
    id: int
    login_id: str | None
    emp_no: str | None
    name: str
    email: str | None
    department: str | None
    role: str
    is_active: bool
    last_login_at: datetime | None
    artifact_count: int


class AdminUserUpdate(ApiModel):
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None


# ---------- 산출물 ----------


class OwnerOut(ApiModel):
    id: int
    name: str
    department: str | None


class ArtifactIn(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = ""
    install_guide: str = ""
    type: str
    status: str = "developing"
    process: str = Field(default="", max_length=200)
    version: str = Field(default="", max_length=50)
    repo_url: str = Field(default="", max_length=500)
    time_saved_min: int | None = Field(default=None, ge=0, le=100_000)
    tools: list[str] = []
    tags: list[str] = []

    @field_validator("title", "summary", "process", "version", "repo_url")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in catalog.ARTIFACT_TYPES:
            raise ValueError(f"알 수 없는 유형입니다: {v}")
        return v

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in catalog.STATUSES:
            raise ValueError(f"알 수 없는 상태입니다: {v}")
        return v

    @field_validator("tools")
    @classmethod
    def _tools(cls, v: list[str]) -> list[str]:
        unknown = [t for t in v if t not in catalog.AI_TOOLS]
        if unknown:
            raise ValueError(f"알 수 없는 AI 도구입니다: {', '.join(unknown)}")
        return list(dict.fromkeys(v))

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().lstrip("#")[:50] for t in v]
        cleaned = list(dict.fromkeys(t for t in cleaned if t))
        if len(cleaned) > 10:
            raise ValueError("태그는 10개까지 입력할 수 있습니다")
        return cleaned


class FileOut(ApiModel):
    id: int
    name: str
    size: int
    content_type: str
    created_at: datetime


class ArtifactSummary(ApiModel):
    id: int
    title: str
    summary: str
    type: str
    status: str
    tools: list[str]
    tags: list[str]
    owner: OwnerOut
    department: str | None
    time_saved_min: int | None
    use_count: int
    file_count: int
    created_at: datetime
    updated_at: datetime


class ArtifactDetail(ArtifactSummary):
    description: str
    install_guide: str
    process: str
    version: str
    repo_url: str
    files: list[FileOut]
    download_count: int
    used_by_me_today: bool
    can_edit: bool


class ArtifactPage(ApiModel):
    items: list[ArtifactSummary]
    total: int
