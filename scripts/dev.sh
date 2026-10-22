#!/usr/bin/env bash
# 개발용: 백엔드(8000)와 Vite(5173, HMR)를 함께 띄웁니다. backend/.env 에 DB·OIDC 값을 넣어두세요.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt; }
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000 &
trap 'kill %1' EXIT
cd "$ROOT/frontend"
[ -d node_modules ] || npm ci
npm run dev
