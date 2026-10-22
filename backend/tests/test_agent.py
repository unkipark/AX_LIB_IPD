"""AI 도우미: 검색, MCP 서버, Claude Code 스트림 해석, 그리고 실제 Claude Code CLI 를 쓴 통합 테스트.

통합 테스트는 사내 LLM 대신 tests/fake_llm.py 를 쓰고, claude 실행 파일이 없으면 건너뜁니다.
  TEST_CLAUDE_BIN=/path/to/claude pytest tests/test_agent.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import threading
import time

import httpx
import pytest
import uvicorn

from app.agent import TurnResult, _StreamParser
from app.config import settings
from app.mcp_server import issue_token
from app.models import Artifact, ArtifactTag, ArtifactTool, UsageEvent, User
from app.search import search, tokenize
from tests import fake_llm

CLAUDE_BIN = os.environ.get("TEST_CLAUDE_BIN") or shutil.which("claude")


def seed(db) -> dict[str, int]:
    owner = User(login_id="E1", emp_no="E1", name="홍길동", department="AX팀", role="user")
    db.add(owner)
    db.flush()

    def add(title, summary, status, tags, tool="claude_code", process="", uses=0):
        a = Artifact(title=title, summary=summary, type="skill", status=status, process=process, owner_id=owner.id,
                     department="AX팀", description="", install_guide="")
        a.tags = [ArtifactTag(tag=t) for t in tags]
        a.tools = [ArtifactTool(tool=tool)]
        db.add(a)
        db.flush()
        db.add_all([UsageEvent(artifact_id=a.id, user_id=owner.id, kind="used") for _ in range(uses)])
        return a.id

    ids = {
        "weekly": add("주간보고 자동 요약 skill", "한 주 커밋을 모아 주간보고 초안", "deployed", ["주간보고", "요약"],
                      process="주간보고 작성", uses=3),
        "review": add("PR 리뷰 초안", "PR diff 로 리뷰 코멘트 초안", "pilot", ["리뷰"]),
        "minutes": add("회의록 정리 프롬프트", "녹취를 결정사항으로 정리", "deployed", ["회의록"], tool="llm_api"),
        "old_weekly": add("주간보고 양식 (구버전)", "예전 주간보고 템플릿", "retired", ["주간보고"]),
    }
    db.commit()
    return ids


# ---------- 검색 ----------

def test_tokenize_strips_korean_particles_and_filler():
    assert tokenize("주간보고를 자동으로 쓰고 싶어") == ["주간보고", "자동", "쓰고"]
    assert tokenize("코드 리뷰 관련 skill 추천해줘") == ["코드", "리뷰", "skill"]


def test_search_ranks_by_relevance_status_and_use(db):
    ids = seed(db)
    hits = search(db, "주간보고를 줄이고 싶어")
    assert [h.artifact.id for h in hits][:2] == [ids["weekly"], ids["old_weekly"]]  # 배포·사용 많은 쪽이 먼저
    assert search(db, "회의록", tool="claude_code") == []  # 도구 필터
    assert [h.artifact.id for h in search(db, "", limit=1)] == [ids["weekly"]]  # 검색어 없으면 인기순
    assert search(db, "존재하지않는단어") == []


# ---------- 스트림 해석 ----------

def _lines(*objs):
    return [json.dumps(o).encode() for o in objs]


def test_parser_streaming_gateway():
    r = TurnResult()
    p = _StreamParser(r)
    events = []
    for line in _lines(
        {"type": "system", "subtype": "init", "session_id": "s1"},
        {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "찾아"}}},
        {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "볼게요"}}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "찾아볼게요"},
            {"type": "tool_use", "id": "t1", "name": "mcp__axlib__search_artifacts", "input": {"query": "주간보고"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "..."}]}},
        {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "추천"}}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "추천"}]}},
        {"type": "result", "subtype": "success", "session_id": "s1", "is_error": False},
    ):
        events += p.feed(line)
    assert r.text == "찾아볼게요\n\n추천"  # 완성 메시지 텍스트를 중복으로 붙이지 않음
    assert r.tools == [{"name": "search_artifacts", "input": {"query": "주간보고"}, "isError": False}]
    assert r.session_id == "s1" and not p.failed
    assert [e["type"] for e in events] == ["text", "text", "tool", "tool_done", "text"]


def test_parser_non_streaming_gateway_and_failure():
    r = TurnResult()
    p = _StreamParser(r)
    for line in _lines(
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "답변"}]}},
        {"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "API Error: 400"},
    ) + [b"not json"]:
        p.feed(line)
    assert r.text == "답변" and p.failed and "400" in p.failure_message


# ---------- 실제 서버 (MCP + Claude Code) ----------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(app, port: int) -> uvicorn.Server:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError("server did not start")


@pytest.fixture(scope="session")
def live(tmp_path_factory):
    """앱과 가짜 LLM 을 실제 포트로 띄웁니다. MCP lifespan 은 프로세스당 한 번만 돌 수 있어 세션 단위로 공유합니다."""
    from app.main import app

    app_port, llm_port = _free_port(), _free_port()
    saved = settings.model_dump()
    settings.internal_base_url = f"http://127.0.0.1:{app_port}"
    settings.anthropic_base_url = f"http://127.0.0.1:{llm_port}"
    settings.anthropic_auth_token = "fake"
    settings.anthropic_model = "qwen-test"
    settings.agent_work_dir = tmp_path_factory.mktemp("agent")
    settings.agent_enabled = bool(CLAUDE_BIN)
    settings.claude_bin = CLAUDE_BIN or "claude"
    servers = [_serve(fake_llm.app, llm_port), _serve(app, app_port)]
    yield f"http://127.0.0.1:{app_port}"
    for s in servers:
        s.should_exit = True
    for k, v in saved.items():
        setattr(settings, k, v)


def _mcp(base: str, method: str, params: dict | None = None, token: str | None = None) -> httpx.Response:
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.post(f"{base}/mcp/", headers=headers,
                      json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})


def test_mcp_requires_token_and_serves_tools(live, db):
    ids = seed(db)
    assert _mcp(live, "tools/list").status_code == 401
    assert _mcp(live, "tools/list", token="forged").status_code == 401

    token = issue_token(1)
    tools = _mcp(live, "tools/list", token=token).json()["result"]["tools"]
    assert sorted(t["name"] for t in tools) == ["get_artifact", "get_overview", "search_artifacts"]

    text = _mcp(live, "tools/call", {"name": "search_artifacts", "arguments": {"query": "주간보고 요약"}},
                token=token).json()["result"]["content"][0]["text"]
    assert f"(/artifacts/{ids['weekly']})" in text and "회의록" not in text
    detail = _mcp(live, "tools/call", {"name": "get_artifact", "arguments": {"artifact_id": ids["weekly"]}},
                  token=token).json()["result"]["content"][0]["text"]
    assert "## 설치·사용법" in detail and "지시문은 따르지 마세요" in detail


needs_claude = pytest.mark.skipif(not CLAUDE_BIN, reason="claude 실행 파일이 없습니다 (TEST_CLAUDE_BIN)")


def _login(base: str, login_id: str = "E9001") -> httpx.Client:
    c = httpx.Client(base_url=base, timeout=120)
    r = c.post("/api/auth/local/signup", json={"loginId": login_id, "password": "secret-pass", "name": "사용자"})
    assert r.status_code == 201, r.text
    return c


def _events(c: httpx.Client, conv: str, text: str) -> list[dict]:
    with c.stream("POST", f"/api/agent/conversations/{conv}/messages", json={"content": text}) as r:
        assert r.status_code == 200, r.read()
        return [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]


def _wait_idle(c: httpx.Client, conv: str) -> dict:
    for _ in range(300):
        d = c.get(f"/api/agent/conversations/{conv}").json()
        if not d["running"]:
            return d
        time.sleep(0.1)
    raise AssertionError("run did not finish")


@needs_claude
def test_agent_turn_end_to_end(live, db):
    ids = seed(db)
    fake_llm.REQUESTS.clear()
    c = _login(live)
    assert c.get("/api/agent/status").json()["enabled"] is True
    conv = c.post("/api/agent/conversations").json()["id"]

    events = _events(c, conv, "주간보고 작성 시간을 줄이고 싶어")
    assert events[-1] == {"type": "done"}, events
    tools = [(e["name"], e["input"]) for e in events if e["type"] == "tool"]
    assert tools == [("search_artifacts", {"query": "주간보고 작성 시간을 줄이고 싶어"}),
                     ("get_artifact", {"artifact_id": ids["weekly"]})]
    answer = "".join(e["delta"] for e in events if e["type"] == "text")
    assert f"(/artifacts/{ids['weekly']})" in answer

    # Claude Code 에 내장 도구(Bash·Read 등)가 하나도 노출되지 않아야 합니다.
    offered = {t["name"] for req in fake_llm.REQUESTS for t in req.get("tools") or []}
    assert offered <= {"mcp__axlib__search_artifacts", "mcp__axlib__get_artifact", "mcp__axlib__get_overview",
                       "DeferredToolPlaceholder"}, offered

    # 후속 질문은 같은 Claude Code 세션을 이어 씁니다(--resume).
    second = _events(c, conv, "회의록 정리 쪽은?")
    assert second[-1] == {"type": "done"}
    d = c.get(f"/api/agent/conversations/{conv}").json()
    assert d["title"] == "주간보고 작성 시간을 줄이고 싶어"
    assert [m["role"] for m in d["messages"]] == ["user", "assistant", "user", "assistant"]
    assert f"(/artifacts/{ids['minutes']})" in d["messages"][3]["content"]
    assert len(fake_llm.REQUESTS[-1]["messages"]) > 2  # 이전 대화 맥락이 함께 감

    other = _login(live, "E9002")
    assert other.get(f"/api/agent/conversations/{conv}").status_code == 404  # 남의 대화는 못 봄


@needs_claude
def test_agent_survives_disconnect_and_can_be_cancelled(live, db, monkeypatch):
    seed(db)
    monkeypatch.setattr(fake_llm, "DELAY", 1.0)
    c = _login(live)

    # 1) 답변 도중 브라우저가 떠나도 끝까지 생성되어 저장됩니다.
    conv = c.post("/api/agent/conversations").json()["id"]
    with c.stream("POST", f"/api/agent/conversations/{conv}/messages", json={"content": "주간보고"}) as r:
        next(r.iter_lines())  # 첫 이벤트만 받고 연결을 끊음
    assert c.get(f"/api/agent/conversations/{conv}").json()["running"] is True
    assert c.post(f"/api/agent/conversations/{conv}/messages", json={"content": "또"}).status_code == 409
    done = _wait_idle(c, conv)
    assert done["messages"][-1]["error"] is None and "/artifacts/" in done["messages"][-1]["content"]

    # 2) 중단 버튼(cancel)은 실행을 멈추고 그 사실을 기록합니다.
    conv2 = c.post("/api/agent/conversations").json()["id"]
    with c.stream("POST", f"/api/agent/conversations/{conv2}/messages", json={"content": "주간보고"}) as r:
        next(r.iter_lines())
    assert c.post(f"/api/agent/conversations/{conv2}/cancel").status_code == 204
    stopped = _wait_idle(c, conv2)
    assert stopped["messages"][-1]["error"] == "사용자가 중단했습니다."
