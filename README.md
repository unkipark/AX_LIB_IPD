# AX 산출물 라이브러리

AI 도구(Claude Code, opencode, LLM API 등)로 업무 프로세스를 개선한 산출물을 부서원이
직접 등록·공유하고, 활용 현황을 한눈에 보는 사내 웹 서비스입니다.

- **현황판**: 등록·사용·누적 절감 시간 KPI, 월별 추이, 상태/유형/AI 도구/부서별 분포, 인기 산출물, 기여자
- **산출물 목록**: 검색, 유형·상태·AI 도구 필터, 내 산출물, 정렬
- **등록/수정**: 웹 폼 + Markdown 설명·설치 가이드 + 첨부파일. 등록자·부서는 계정 정보로 자동 입력
- **계정**: 사번 + 비밀번호로 시작하고, 나중에 사내 SSO(OIDC)로 전환 (`AUTH_MODE`). 전환 시 사번으로 기존 계정이 이어짐
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
│   │   ├── auth.py            세션·현재 사용자·내 정보 (공통)
│   │   ├── auth_local.py      ★ 사번 + 비밀번호 로그인·가입 (AUTH_MODE=local)
│   │   ├── auth_oidc.py       ★ 사내 SSO 로그인 (AUTH_MODE=oidc)
│   │   ├── passwords.py       비밀번호 해시 (표준 라이브러리 scrypt)
│   │   ├── catalog.py         ★ 분류 체계(유형·상태·AI 도구) — 여기만 고치면 화면에 반영
│   │   ├── models.py          테이블 정의
│   │   ├── schemas.py         API 입출력 (camelCase)
│   │   └── routers/
│   │       ├── artifacts.py   산출물 CRUD · 첨부파일 · 사용 기록
│   │       ├── dashboard.py   현황판 집계
│   │       └── admin.py       사용자 관리 (관리자)
│   ├── alembic/               DB 마이그레이션
│   └── tests/                 pytest (실제 PostgreSQL 사용)
├── frontend/                  Vite + React + TS + shadcn/ui + Recharts
│   └── src/
│       ├── pages/             Dashboard · Catalog · ArtifactDetail · ArtifactForm · Login · Profile · AdminUsers
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
| `users` | local: 가입·관리자 생성, 이름·부서는 본인이 수정. oidc: 첫 SSO 로그인 때 생성, 매 로그인마다 IdP 값으로 갱신. 둘은 사번(`emp_no`)으로 연결 |
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
vi .env                         # PUBLIC_BASE_URL, POSTGRES_PASSWORD, SESSION_SECRET, ADMIN_IDS 채우기
docker compose up -d --build
```

브라우저에서 `PUBLIC_BASE_URL` (예: `http://10.0.0.10:8000`) 접속 → 로그인 화면 → 가입 → 현황판.
`ADMIN_IDS` 에 넣은 사번으로 가입하면 관리자가 되고, 상단에 '사용자 관리' 메뉴가 생깁니다.

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

## 3. 인증

`AUTH_MODE` 로 고릅니다. 기본값은 `local` 입니다.

### 3-1. 사번 + 비밀번호 (`AUTH_MODE=local`)

- **가입**: 로그인 화면의 '가입' 탭에서 사번·이름·부서·비밀번호(8자 이상)를 입력합니다.
  부서는 기존 표기를 자동완성으로 보여줘, 같은 부서가 여러 표기로 갈라지지 않게 합니다.
  `LOCAL_SIGNUP=false` 면 가입 탭이 사라지고 관리자가 '사용자 관리 → 계정 만들기'로 만듭니다.
- **로그인 ID 가 사번인 이유**: 나중에 SSO 로 바꾸면 SSO 의 사번 claim 으로 기존 계정을 찾아
  연결하므로, 그동안의 산출물·사용 기록이 그대로 이어집니다.
- **비밀번호**: 표준 라이브러리 scrypt 로 해시해 저장합니다. 연속 5회 실패하면 10분 잠깁니다
  (`LOGIN_MAX_FAILURES`, `LOGIN_LOCK_MINUTES`).
- **비밀번호 분실**: 관리자가 '사용자 관리'에서 초기화하면 임시 비밀번호가 화면에 나옵니다.
  본인에게 전달하고, 로그인 후 '내 정보'(상단 이름 클릭)에서 바꾸도록 안내하세요.
- **퇴사·이동**: '사용자 관리'에서 비활성화하면 바로 로그인이 막히고, 등록한 산출물은 남습니다.
- **주의 (본인 확인 없음)**: 자가 가입은 사번이 본인 것인지 확인하지 않습니다. 배포 직후 관리자가
  `ADMIN_IDS` 의 사번으로 **먼저** 가입하고, '사용자 관리'에서 낯선 계정이 보이면 비활성화하세요.
  이 위험을 없애려면 `LOCAL_SIGNUP=false` 로 두고 관리자가 계정을 만들어 주면 됩니다.
- **주의**: `http://IP` 로 서비스하면 비밀번호가 암호화되지 않은 채 사내망을 지나갑니다.
  사내망 전용이라도 가능하면 HTTPS 리버스 프록시를 붙이고 `SESSION_COOKIE_SECURE=true` 로 두세요.

### 3-2. 사내 SSO (`AUTH_MODE=oidc`)

`.env` 에서 `AUTH_MODE=oidc` 로 바꾸고 아래 `OIDC_*` 값을 채운 뒤 재시작하면 됩니다
(`docker compose up -d`). DB 변경은 필요 없습니다.

- 로그인 화면에는 'SSO 로그인' 버튼만 남고, 가입·비밀번호 기능은 꺼집니다.
- 첫 SSO 로그인 때 `OIDC_CLAIM_EMP_NO` 의 사번과 같은 local 계정이 있으면 그 계정에 연결됩니다.
  사번 claim 이름이 맞지 않으면 연결되지 않고 새 계정이 생기므로, 전환 전에 claim 이름을 확인하세요.

#### SSO 담당 부서에 등록 요청할 정보

| 항목 | 값 |
|---|---|
| Grant type | Authorization Code |
| Redirect URI | `<PUBLIC_BASE_URL>/api/auth/callback` (예: `http://10.0.0.10:8000/api/auth/callback`) |
| Post-logout redirect URI | `<PUBLIC_BASE_URL>/` |
| Scope | `openid profile email` (+ 부서 정보가 별도 scope 이면 추가) |
| 필요한 claim | 사용자 고유 ID, 사번, 이름, 이메일, **부서명** |

발급받은 `client_id` / `client_secret` 과 discovery URL 을 `.env` 에 넣습니다.

#### claim 매핑

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

#### 확인할 점

- **IP 기반 http 주소**: IdP 가 `http://<IP>` redirect URI 를 거부하면 사내 DNS 이름과 HTTPS 가
  필요합니다. 이때는 앞단에 리버스 프록시(nginx 등)로 TLS 를 붙이고
  `PUBLIC_BASE_URL=https://...`, `SESSION_COOKIE_SECURE=true` 로 바꾸세요.
- **사내 CA 인증서**: IdP 가 사내 CA 로 서명돼 있으면 CA 파일을 컨테이너에 마운트하고
  `OIDC_CA_BUNDLE` 에 그 경로를 지정합니다.
- **관리자**: `ADMIN_IDS` 에 사번(또는 id claim 값)을 쉼표로 넣으면 다음 로그인부터 관리자 권한이
  붙습니다. 관리자는 모든 산출물을 수정·삭제하고 사용자를 관리할 수 있습니다.

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

# backend/.env 에 DATABASE_URL 지정 후 (기본 AUTH_MODE=local 이라 IdP 없이 개발 가능)
./scripts/dev.sh             # 백엔드 :8000 + Vite :5173 (HMR, /api 는 8000 으로 프록시)
```

SSO 를 개발 환경에서 시험할 때는 콜백이 `:8000` 으로 돌아오므로 `PUBLIC_BASE_URL=http://localhost:8000`
으로 두고, 로그인 후 `:5173` 으로 접속하면 같은 쿠키로 동작합니다.

### 테스트

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://axlib:axlib@localhost:5432/axlib_test .venv/bin/pytest
```

산출물 테스트는 FastAPI 의존성 오버라이드로 로그인 사용자를 주입하고, 계정 테스트
(`test_local_auth.py`)는 실제 세션 쿠키로 가입·로그인·잠금·관리자 기능과 SSO 전환 시 계정 연결을 검증합니다.

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
