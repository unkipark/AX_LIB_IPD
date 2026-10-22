# AX 산출물 라이브러리

AI 도구(Claude Code, opencode, LLM API 등)로 업무 프로세스를 개선한 산출물을 부서원이
직접 등록·공유하고, 활용 현황을 한눈에 보는 사내 웹 서비스입니다.

- **현황판**: 등록·사용·누적 절감 시간 KPI, 월별 추이, 상태/유형/AI 도구/부서별 분포, 인기 산출물, 기여자
- **산출물 목록**: 검색, 유형·상태·AI 도구 필터, 내 산출물, 정렬
- **등록/수정**: 웹 폼 + Markdown 설명·설치 가이드 + 첨부파일. 등록자·부서는 SSO 정보로 자동 입력
- **사용 기록**: "써봤어요"(사용자·산출물·일자당 1회) + 다운로드 수 → 절감 시간 집계에 반영

UI 는 [hapo_ui](https://github.com/unkipark/hapo_ui) 프론트엔드(Vite + React + shadcn/ui + Tailwind,
테마·팔레트 시스템)를 템플릿으로 가져와 만들었습니다.

---

## 1. 구성

```
AX_LIB_IPD/
├── docker-compose.yml         PostgreSQL + 앱 컨테이너
├── Dockerfile                 프론트 빌드 → FastAPI 이미지에 static 으로 포함
├── .env.example               ★ 배포 설정 (SSO·DB·세션)
├── backend/                   FastAPI + SQLAlchemy 2 + Alembic
│   ├── app/
│   │   ├── main.py            라우터·세션 미들웨어·SPA 정적 서빙
│   │   ├── auth.py            ★ 사내 SSO(OIDC) 로그인, 사용자 upsert
│   │   ├── catalog.py         ★ 분류 체계(유형·상태·AI 도구) — 여기만 고치면 화면에 반영
│   │   ├── models.py          테이블 정의
│   │   ├── schemas.py         API 입출력 (camelCase)
│   │   └── routers/
│   │       ├── artifacts.py   산출물 CRUD · 첨부파일 · 사용 기록
│   │       └── dashboard.py   현황판 집계
│   ├── alembic/               DB 마이그레이션
│   └── tests/                 pytest (실제 PostgreSQL 사용)
├── frontend/                  Vite + React + TS + shadcn/ui + Recharts
│   └── src/
│       ├── pages/             Dashboard · Catalog · ArtifactDetail · ArtifactForm
│       ├── components/        Layout · ArtifactCard · StatusBadge · Markdown · ui/
│       └── lib/               api.ts · meta.ts · theme.ts
└── scripts/
    ├── export-images.sh       (외부망) 이미지 빌드 → tar.gz
    ├── import-images.sh       (폐쇄망) tar.gz → docker load
    ├── backup.sh              DB 덤프 + 첨부파일 백업
    └── dev.sh                 개발 서버 (백엔드 + Vite HMR)
```

### 데이터 모델

| 테이블 | 내용 |
|---|---|
| `users` | SSO 로그인 시 자동 생성. 이름·부서·이메일은 매 로그인마다 IdP 값으로 갱신 |
| `artifacts` | 제목, 요약, 설명(MD), 설치 가이드(MD), 유형, 상태, 개선 대상 업무, 버전, 저장소 URL, 1회 절감 시간(분), 등록자, 등록 당시 부서 |
| `artifact_tools` / `artifact_tags` | 사용 AI 도구, 태그 (집계·필터용으로 별도 테이블) |
| `artifact_files` | 첨부파일 메타데이터. 실제 파일은 `UPLOAD_DIR/<산출물 id>/` |
| `usage_events` | `used`("써봤어요"), `download` 기록 |

**누적 절감 시간** = Σ(산출물의 1회 절감 시간 × "써봤어요" 수).
부서는 등록 시점 값을 산출물에 따로 저장하므로, 조직 개편 후에도 실적이 원래 부서에 남습니다.

---

## 2. 배포 (Docker Compose)

```bash
cp .env.example .env
vi .env                         # PUBLIC_BASE_URL, POSTGRES_PASSWORD, SESSION_SECRET, OIDC_* 채우기
docker compose up -d --build
```

브라우저에서 `PUBLIC_BASE_URL` (예: `http://10.0.0.10:8000`) 접속 → SSO 로그인 → 현황판.

- 컨테이너가 시작될 때마다 `alembic upgrade head` 가 먼저 돌아 DB 스키마를 최신으로 맞춥니다.
- 데이터는 `./volumes/postgres`, 첨부파일은 `./volumes/uploads` 에 남습니다.
- 업데이트: `git pull && docker compose up -d --build`

### 폐쇄망 서버로 반입하는 경우

서버에서 Docker Hub·npm·PyPI 에 접근할 수 없으면, 외부망에서 이미지를 만들어 가져갑니다.

```bash
# 외부망
./scripts/export-images.sh                 # → dist-images/ax-lib-<버전>.tar.gz (앱 + postgres 이미지)

# 폐쇄망 서버 (저장소 소스 + tar.gz 반입 후)
./scripts/import-images.sh dist-images/ax-lib-<버전>.tar.gz
docker compose up -d                       # --build 없이 실행
```

---

## 3. 사내 SSO (OIDC) 연동

### SSO 담당 부서에 등록 요청할 정보

| 항목 | 값 |
|---|---|
| Grant type | Authorization Code |
| Redirect URI | `<PUBLIC_BASE_URL>/api/auth/callback` (예: `http://10.0.0.10:8000/api/auth/callback`) |
| Post-logout redirect URI | `<PUBLIC_BASE_URL>/` |
| Scope | `openid profile email` (+ 부서 정보가 별도 scope 이면 추가) |
| 필요한 claim | 사용자 고유 ID, 사번, 이름, 이메일, **부서명** |

발급받은 `client_id` / `client_secret` 과 discovery URL 을 `.env` 에 넣습니다.

### claim 매핑

IdP 마다 claim 이름이 다르므로 `.env` 에서 매핑합니다. 중첩 claim 은 점으로 지정합니다.

```ini
OIDC_CLAIM_ID=sub                  # 사용자 고유 키 (변하지 않는 값이어야 함)
OIDC_CLAIM_EMP_NO=employee_number
OIDC_CLAIM_NAME=name
OIDC_CLAIM_EMAIL=email
OIDC_CLAIM_DEPARTMENT=department   # 예) org.dept_name
```

id_token 과 userinfo 응답을 합쳐서 읽습니다. 부서처럼 확장 claim 을 userinfo 에만 주는 IdP 도
그대로 동작합니다.

### 확인할 점

- **IP 기반 http 주소**: IdP 가 `http://<IP>` redirect URI 를 거부하면 사내 DNS 이름과 HTTPS 가
  필요합니다. 이때는 앞단에 리버스 프록시(nginx 등)로 TLS 를 붙이고
  `PUBLIC_BASE_URL=https://...`, `SESSION_COOKIE_SECURE=true` 로 바꾸세요.
- **사내 CA 인증서**: IdP 가 사내 CA 로 서명돼 있으면 CA 파일을 컨테이너에 마운트하고
  `OIDC_CA_BUNDLE` 에 그 경로를 지정합니다.
- **관리자**: `ADMIN_IDS` 에 id claim 값 또는 사번을 쉼표로 넣으면 다음 로그인부터 관리자 권한이
  붙습니다. 관리자는 모든 산출물을 수정·삭제할 수 있습니다.

---

## 4. 분류 체계 바꾸기

유형·상태·AI 도구 목록은 `backend/app/catalog.py` 한 곳에 있습니다. 항목을 추가하면
등록 폼·필터·현황판에 바로 나타나고, DB 마이그레이션은 필요 없습니다.
이미 쓰인 key 는 지우거나 바꾸지 말고 라벨만 바꾸세요.

---

## 5. 개발

```bash
# PostgreSQL 준비 (로컬 또는 docker compose up -d db)
createdb axlib && createdb axlib_test

# backend/.env 에 DATABASE_URL, OIDC_* (개발용 IdP client) 지정 후
./scripts/dev.sh             # 백엔드 :8000 + Vite :5173 (HMR, /api 는 8000 으로 프록시)
```

개발 중 SSO 로그인 콜백이 `:8000` 으로 돌아오므로 `PUBLIC_BASE_URL=http://localhost:8000` 으로
두고, 로그인 후 `:5173` 으로 접속하면 같은 쿠키로 동작합니다.

### 테스트

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://axlib:axlib@localhost:5432/axlib_test .venv/bin/pytest
```

테스트는 SSO 왕복 대신 FastAPI 의존성 오버라이드로 로그인 사용자를 주입합니다.
claim 매핑(`upsert_user`)은 별도 테스트로 검증합니다.

### 스키마 변경

```bash
cd backend
# models.py 수정 후
.venv/bin/alembic revision --autogenerate -m "설명"
.venv/bin/alembic upgrade head
```

---

## 6. 운영

- **백업**: `scripts/backup.sh` 를 cron 에 등록 (DB `pg_dump` + 첨부파일 tar, 30일 보관)
- **복원**: `docker compose exec -T db pg_restore -U axlib -d axlib --clean < backups/<날짜>/axlib.dump`
- **첨부파일 용량 제한**: `MAX_UPLOAD_MB` (기본 100MB)

---

## 7. 다음 단계 (로드맵)

1. **Gitea 연동**: 저장소 URL 에서 README 자동 수집, 버전 태그 동기화
2. **Claude Code 마켓플레이스**: skill/plugin 유형을 `.claude-plugin/marketplace.json` 으로 자동 생성해
   `/plugin marketplace add` 한 줄로 설치
3. **후기·댓글**, 산출물 간 연관 추천
4. **`/ax-register` skill**: 작업 폴더를 분석해 메타데이터 초안을 만들고 API 로 등록
