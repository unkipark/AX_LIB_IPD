# ── 1단계: 프론트엔드 빌드 ─────────────────────────────────────────
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── 2단계: Claude Code CLI (AI 도우미용) ───────────────────────────
# 사내 LLM 게이트웨이와 이미 검증된 버전으로 맞추세요. 버전마다 API 요청 형식이 조금씩 다릅니다.
#   docker compose build --build-arg CLAUDE_CODE_VERSION=2.1.42
FROM node:22-slim AS claude
ARG CLAUDE_CODE_VERSION=2.1.42
RUN npm install -g --omit=optional @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# ── 3단계: 백엔드 런타임 ───────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=claude /usr/local/bin/node /usr/local/bin/node
COPY --from=claude /usr/local/lib/node_modules/@anthropic-ai/claude-code /opt/claude-code
RUN ln -s /opt/claude-code/cli.js /usr/local/bin/claude && claude --version
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV STATIC_DIR=/app/static UPLOAD_DIR=/data/uploads AGENT_WORK_DIR=/data/agent
EXPOSE 8000
# 시작할 때마다 DB 스키마를 최신으로 맞춘 뒤 서버를 띄웁니다.
# AI 도우미의 실행 상태를 메모리에 두므로 worker 는 1개로 둡니다.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
