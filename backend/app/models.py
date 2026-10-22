"""DB 테이블 정의. 스키마를 바꾸면 alembic revision 을 함께 추가하세요."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """local 모드: 가입 시 생성되고 이름·부서는 본인이 관리합니다.
    oidc 모드: SSO 로그인 시 자동 생성·갱신되고, 이름·부서는 매 로그인마다 IdP 값으로 덮어씁니다.
    두 방식은 사번(emp_no)으로 이어집니다."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True)  # OIDC id claim (기본 sub)
    login_id: Mapped[str | None] = mapped_column(String(50), unique=True)  # local 로그인 ID (= 사번)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    emp_no: Mapped[str | None] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 관리자가 만든 뒤 아직 로그인 전이면 비어 있음


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")  # Markdown
    install_guide: Mapped[str] = mapped_column(Text, default="")  # Markdown
    type: Mapped[str] = mapped_column(String(32))  # catalog.ARTIFACT_TYPES
    status: Mapped[str] = mapped_column(String(32))  # catalog.STATUSES
    process: Mapped[str] = mapped_column(String(200), default="")  # 개선 대상 업무 프로세스
    version: Mapped[str] = mapped_column(String(50), default="")
    repo_url: Mapped[str] = mapped_column(String(500), default="")
    # 1회 사용 시 절감되는 시간(분). 현황판의 누적 절감 시간 = 이 값 × 사용 기록 수
    time_saved_min: Mapped[int | None] = mapped_column(Integer)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 등록 당시 부서. 이후 조직 개편이 있어도 실적이 원래 부서에 남도록 따로 저장합니다.
    department: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship()
    tools: Mapped[list[ArtifactTool]] = relationship(cascade="all, delete-orphan", order_by="ArtifactTool.tool")
    tags: Mapped[list[ArtifactTag]] = relationship(cascade="all, delete-orphan", order_by="ArtifactTag.tag")
    files: Mapped[list[ArtifactFile]] = relationship(
        cascade="all, delete-orphan", order_by="ArtifactFile.created_at"
    )


class ArtifactTool(Base):
    __tablename__ = "artifact_tools"

    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    tool: Mapped[str] = mapped_column(String(32), primary_key=True)  # catalog.AI_TOOLS


class ArtifactTag(Base):
    __tablename__ = "artifact_tags"

    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(50), primary_key=True)


class ArtifactFile(Base):
    __tablename__ = "artifact_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(300))
    stored_name: Mapped[str] = mapped_column(String(100))  # upload_dir/<artifact_id>/<stored_name>
    size: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsageEvent(Base):
    """kind = download | used.  'used' 는 "써봤어요" 버튼으로, 사용자·산출물·일자당 1건입니다."""

    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_artifact_kind", "artifact_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AgentConversation(Base):
    """AI 도우미 대화. claude_session_id 로 Claude Code 세션을 이어갑니다(--resume)."""

    __tablename__ = "agent_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(100), default="새 대화")
    claude_session_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list[AgentMessage]] = relationship(
        cascade="all, delete-orphan", order_by="AgentMessage.id"
    )


class AgentMessage(Base):
    """대화 기록. 감사(audit)와 '사람들이 무엇을 찾는지' 분석에 씁니다."""

    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    # assistant 메시지가 호출한 도구 [{name, input, isError}]
    tools: Mapped[list | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
