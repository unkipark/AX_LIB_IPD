"""테스트용 가짜 Anthropic Messages API.

사내 LLM 없이 Claude Code ↔ MCP 서버 ↔ 앱 배선을 검증하려고, 정해진 순서로만 답합니다.
  1) 사용자 질문 → "찾아볼게요" + search_artifacts(query=질문)
  2) 검색 결과에 id 가 있으면 → get_artifact(첫 번째 id)
  3) 상세를 받으면 → 첫 산출물 링크로 추천 답변 (결과가 없으면 "없습니다")
도구가 없는 요청(제목 생성 등 보조 호출)에는 "ok" 로 답합니다.

실행: uvicorn tests.fake_llm:app --port 9100   (ANTHROPIC_BASE_URL=http://127.0.0.1:9100)
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

# 받은 요청 기록 (테스트에서 Claude Code 가 보낸 도구 목록 등을 확인)
REQUESTS: list[dict[str, Any]] = []
# 응답마다 기다릴 시간(초). 테스트에서 '답변 도중 연결 끊김·중단' 상황을 만들 때 씁니다.
DELAY = 0.0


def _blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    return [{"type": "text", "text": content}] if isinstance(content, str) else list(content or [])


def _tool_result_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in content or [] if isinstance(c, dict))


def _plan(body: dict[str, Any]) -> list[dict[str, Any]]:
    """다음 assistant 응답의 content 블록들."""
    tool_names = {t.get("name") for t in body.get("tools") or []}
    search = next((n for n in tool_names if n and n.endswith("search_artifacts")), None)
    detail = next((n for n in tool_names if n and n.endswith("get_artifact")), None)
    if not search:
        return [{"type": "text", "text": "ok"}]

    # 최신 Claude Code 는 질문 뒤에 환경 정보를 role=system 메시지로 덧붙이므로 user 메시지만 봅니다.
    last = next(m for m in reversed(body["messages"]) if m.get("role") == "user")
    results = [b for b in _blocks(last) if b.get("type") == "tool_result"]
    if not results:
        question = next(
            (b["text"] for b in _blocks(last)
             if b.get("type") == "text" and not b["text"].lstrip().startswith(("<", "#"))),
            "",
        )
        return [
            {"type": "text", "text": "라이브러리에서 찾아볼게요."},
            {"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:12]}", "name": search, "input": {"query": question}},
        ]

    text = _tool_result_text(results[-1])
    if "## 설명" not in text:  # 검색 결과
        ids = re.findall(r"id=(\d+)", text)
        if not ids:
            return [{"type": "text", "text": "맞는 산출물이 없습니다. 아이디어로 등록해 보세요."}]
        return [{"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:12]}", "name": detail,
                 "input": {"artifact_id": int(ids[0])}}]

    m = re.search(r"\[(.+?)\]\((/artifacts/\d+)\)", text)
    title, link = (m.group(1), m.group(2)) if m else ("?", "#")
    return [{"type": "text", "text": f"**[{title}]({link})** 을(를) 추천합니다.\n\n다음 행동: 상세 페이지에서 설치 가이드를 따라 해 보세요."}]


def _message(content: list[dict[str, Any]], model: str) -> dict[str, Any]:
    stop = "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"
    return {"id": f"msg_{uuid.uuid4().hex[:12]}", "type": "message", "role": "assistant", "model": model,
            "content": content, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 10}}


def _sse(message: dict[str, Any]):
    def ev(name: str, data: dict[str, Any]) -> str:
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield ev("message_start", {"type": "message_start", "message": {**message, "content": [], "stop_reason": None}})
    for i, block in enumerate(message["content"]):
        if block["type"] == "text":
            yield ev("content_block_start", {"type": "content_block_start", "index": i,
                                             "content_block": {"type": "text", "text": ""}})
            for k in range(0, len(block["text"]), 8):  # 조각내서 보내 스트리밍을 흉내 냅니다
                yield ev("content_block_delta", {"type": "content_block_delta", "index": i,
                                                 "delta": {"type": "text_delta", "text": block["text"][k:k + 8]}})
        else:
            yield ev("content_block_start", {"type": "content_block_start", "index": i,
                                             "content_block": {**block, "input": {}}})
            yield ev("content_block_delta", {"type": "content_block_delta", "index": i,
                                             "delta": {"type": "input_json_delta",
                                                       "partial_json": json.dumps(block["input"], ensure_ascii=False)}})
        yield ev("content_block_stop", {"type": "content_block_stop", "index": i})
    yield ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": message["stop_reason"],
                                                                 "stop_sequence": None},
                               "usage": {"output_tokens": 10}})
    yield ev("message_stop", {"type": "message_stop"})


@app.post("/v1/messages")
async def messages(request: Request):
    body = await request.json()
    REQUESTS.append(body)
    if DELAY and body.get("tools"):
        await asyncio.sleep(DELAY)
    message = _message(_plan(body), body.get("model", "fake"))
    if body.get("stream"):
        return StreamingResponse(_sse(message), media_type="text/event-stream")
    return JSONResponse(message)


@app.post("/v1/messages/count_tokens")
async def count_tokens():
    return {"input_tokens": 10}
