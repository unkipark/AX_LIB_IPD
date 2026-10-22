"""산출물 분류 체계. 화면의 선택지·라벨은 모두 /api/meta 를 통해 여기서 나갑니다.

항목을 추가할 때는 이 파일만 고치면 됩니다. DB 에는 key 문자열만 저장하므로
마이그레이션이 필요 없습니다. 단, 이미 쓰인 key 를 지우거나 바꾸면 기존 데이터가
'알 수 없음'으로 보이니 라벨만 바꾸세요.
"""
from __future__ import annotations

ARTIFACT_TYPES: dict[str, str] = {
    "skill": "Skill",
    "slash_command": "Slash Command",
    "plugin": "Plugin",
    "mcp_server": "MCP 서버",
    "agent": "Agent / Subagent",
    "prompt": "프롬프트",
    "script": "스크립트 / 앱",
    "workflow": "워크플로",
    "guide": "가이드 / 사례 문서",
    "other": "기타",
}

STATUSES: dict[str, str] = {
    "idea": "아이디어",
    "developing": "개발 중",
    "pilot": "파일럿",
    "deployed": "배포",
    "retired": "중단",
}

AI_TOOLS: dict[str, str] = {
    "claude_code": "Claude Code",
    "opencode": "opencode",
    "llm_api": "LLM API",
    "copilot": "GitHub Copilot",
    "cursor": "Cursor",
    "other": "기타",
}


def meta() -> dict:
    def pairs(d: dict[str, str]) -> list[dict[str, str]]:
        return [{"key": k, "label": v} for k, v in d.items()]

    return {"types": pairs(ARTIFACT_TYPES), "statuses": pairs(STATUSES), "tools": pairs(AI_TOOLS)}
