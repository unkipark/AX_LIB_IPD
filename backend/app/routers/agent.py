"""AI 도우미 대화 API. 답변은 Server-Sent Events 로 흘려보냅니다."""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..agent import TurnResult, agent_available, run_turn
from ..auth import current_user
from ..config import settings
from ..db import SessionLocal, get_db
from ..models import AgentConversation, AgentMessage, User, utcnow
from ..schemas import ApiModel

router = APIRouter(prefix="/api/agent", tags=["agent"])

# 실행 중인 답변. 브라우저가 떠나도(링크 클릭·새로고침) 끝까지 돌고 DB 에 저장되도록
# 요청과 분리된 작업으로 돌립니다. 대화마다 하나만 실행합니다(세션이 꼬이지 않게).
_runs: dict[str, asyncio.Task] = {}


class MessageIn(ApiModel):
    content: str = Field(min_length=1, max_length=2000)


def _own(db: Session, conversation_id: str, user: User) -> AgentConversation:
    conv = db.get(AgentConversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return conv


@router.get("/status")
def status(_: User = Depends(current_user)):
    ok, reason = agent_available()
    return {"enabled": ok, "reason": reason, "model": settings.anthropic_model if ok else ""}


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(
        select(AgentConversation).where(AgentConversation.user_id == user.id)
        .order_by(AgentConversation.updated_at.desc()).limit(50)
    ).all()
    return [{"id": c.id, "title": c.title, "updatedAt": c.updated_at} for c in rows]


@router.post("/conversations", status_code=201)
def create_conversation(db: Session = Depends(get_db), user: User = Depends(current_user)):
    conv = AgentConversation(id=str(uuid.uuid4()), user_id=user.id)
    db.add(conv)
    db.commit()
    return {"id": conv.id, "title": conv.title, "updatedAt": conv.updated_at}


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    conv = _own(db, conversation_id, user)
    return {
        "id": conv.id,
        "title": conv.title,
        "running": conversation_id in _runs,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "tools": m.tools or [], "error": m.error,
             "createdAt": m.created_at}
            for m in conv.messages
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    conv = _own(db, conversation_id, user)
    if task := _runs.get(conversation_id):
        task.cancel()
    db.delete(conv)
    db.commit()


def _start_turn(conversation_id: str, user_id: int, content: str) -> str | None:
    """사용자 메시지를 저장하고, 이어갈 Claude Code 세션 id 를 돌려줍니다."""
    with SessionLocal() as db:
        conv = db.get(AgentConversation, conversation_id)
        assert conv is not None
        if not conv.messages:
            conv.title = content.strip().splitlines()[0][:40] or "새 대화"
        db.add(AgentMessage(conversation_id=conv.id, role="user", content=content))
        conv.updated_at = utcnow()
        db.commit()
        return conv.claude_session_id


def _finish_turn(conversation_id: str, result: TurnResult) -> None:
    with SessionLocal() as db:
        conv = db.get(AgentConversation, conversation_id)
        if conv is None:  # 답변 도중 대화가 삭제된 경우
            return
        if result.session_id and not result.error:
            conv.claude_session_id = result.session_id
        db.add(AgentMessage(conversation_id=conv.id, role="assistant", content=result.text,
                            tools=result.tools or None, error=(result.error or None) and result.error[:500]))
        conv.updated_at = utcnow()
        db.commit()


async def _drive(conversation_id: str, user_id: int, content: str, queue: asyncio.Queue) -> None:
    """질문 하나를 끝까지 실행하고 기록합니다. 이벤트는 듣는 브라우저가 있으면 queue 로 전달됩니다."""
    result = TurnResult()
    try:
        resume = await run_in_threadpool(_start_turn, conversation_id, user_id, content)
        async for event in run_turn(conversation_id, user_id, content, resume, result):
            queue.put_nowait(event)
    except asyncio.CancelledError:
        result.error = "사용자가 중단했습니다."
        queue.put_nowait({"type": "error", "message": result.error})
    except Exception as e:  # noqa: BLE001 — 실패해도 대화 기록은 남겨야 합니다.
        result.error = f"실행 중 오류: {e}"
        queue.put_nowait({"type": "error", "message": result.error})
    finally:
        await asyncio.shield(run_in_threadpool(_finish_turn, conversation_id, result))
        _runs.pop(conversation_id, None)
        queue.put_nowait(None)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str, body: MessageIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    ok, reason = agent_available()
    if not ok:
        raise HTTPException(503, f"AI 도우미를 사용할 수 없습니다: {reason}")
    _own(db, conversation_id, user)
    if conversation_id in _runs:
        raise HTTPException(409, "이전 질문에 답하는 중입니다. 끝난 뒤 다시 보내주세요")
    queue: asyncio.Queue = asyncio.Queue()
    _runs[conversation_id] = asyncio.create_task(_drive(conversation_id, user.id, body.content, queue))

    async def stream() -> AsyncIterator[str]:
        # 브라우저가 연결을 끊으면 여기만 멈추고, 실행(_drive)은 계속됩니다.
        while (event := await queue.get()) is not None:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/conversations/{conversation_id}/cancel", status_code=204)
def cancel(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _own(db, conversation_id, user)
    if task := _runs.get(conversation_id):
        task.cancel()
