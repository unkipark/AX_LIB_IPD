"""AI 도우미용 산출물 검색.

목록 화면의 검색(한 구절 ILIKE)과 달리, LLM 이 보내는 자연어 검색어
("주간보고를 자동으로 요약")를 단어로 나눠 필드별 가중치로 점수를 매깁니다.
부서 규모(수백~수천 건)에서는 전체를 메모리에서 채점해도 충분히 빠르고,
DB 종류나 확장(pg_trgm 등)에 의존하지 않습니다.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import Artifact, UsageEvent

# 한국어 검색어 끝의 조사. "보고서를" → "보고서" 처럼 떼어 내고 찾습니다.
_JOSA = ("으로", "에서", "에게", "까지", "부터", "처럼", "하고", "이랑", "을", "를", "이", "가", "은", "는",
         "에", "의", "로", "와", "과", "도", "만")
# 질문 끝맺음·군더더기. 검색 점수에 도움이 안 되고, 설명 본문에 우연히 걸려 엉뚱한 결과를 올립니다.
_STOPWORDS = {"관련", "있어", "있나", "있나요", "있는", "있을까", "싶어", "싶은데", "찾아", "찾아줘", "추천", "추천해줘",
              "알려줘", "알려주세요", "해줘", "주세요", "어떤", "방법", "the", "a", "an", "for", "to"}

# 필드별 가중치: 제목·태그에 맞으면 설명 본문보다 훨씬 관련도가 높습니다.
_WEIGHTS = {"title": 3.0, "tags": 3.0, "process": 2.0, "summary": 2.0, "description": 1.0}
_STATUS_BONUS = {"deployed": 1.0, "pilot": 0.5, "developing": 0.2, "idea": 0.0, "retired": -1.0}


def tokenize(query: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.split(r"[\s,./·|()\[\]{}\"'!?~:;]+", query.lower()):
        word = raw.strip("#-_")
        for josa in _JOSA:
            if len(word) > len(josa) + 1 and word.endswith(josa):
                word = word[: -len(josa)]
                break
        if len(word) >= 2 and word not in _STOPWORDS:
            tokens.append(word)
    return list(dict.fromkeys(tokens))


@dataclass
class Hit:
    artifact: Artifact
    score: float
    uses: int


def search(
    db: Session, query: str = "", type: str = "", tool: str = "", status: str = "", limit: int = 8
) -> list[Hit]:
    stmt = select(Artifact).options(
        selectinload(Artifact.owner), selectinload(Artifact.tools), selectinload(Artifact.tags)
    )
    if type:
        stmt = stmt.where(Artifact.type == type)
    if status:
        stmt = stmt.where(Artifact.status == status)
    artifacts = [a for a in db.scalars(stmt).all() if not tool or tool in {t.tool for t in a.tools}]

    uses = dict(
        db.execute(
            select(UsageEvent.artifact_id, func.count()).where(UsageEvent.kind == "used").group_by(UsageEvent.artifact_id)
        ).all()
    )
    tokens = tokenize(query)
    hits: list[Hit] = []
    for a in artifacts:
        n_uses = uses.get(a.id, 0)
        popularity = math.log1p(n_uses) * 0.5 + _STATUS_BONUS.get(a.status, 0.0)
        if not tokens:
            hits.append(Hit(a, popularity, n_uses))
            continue
        fields = {
            "title": a.title.lower(),
            "tags": " ".join(t.tag.lower() for t in a.tags),
            "process": a.process.lower(),
            "summary": a.summary.lower(),
            "description": a.description.lower(),
        }
        relevance = sum(
            max((w for f, w in _WEIGHTS.items() if tok in fields[f]), default=0.0) for tok in tokens
        )
        if relevance > 0:
            hits.append(Hit(a, relevance + popularity, n_uses))

    hits.sort(key=lambda h: (h.score, h.artifact.updated_at), reverse=True)
    return hits[: max(1, min(limit, 20))]
