"""테스트는 실제 PostgreSQL 에 붙습니다. TEST_DATABASE_URL 로 별도 DB 를 지정하세요.

  createdb axlib_test
  TEST_DATABASE_URL=postgresql+psycopg://axlib:axlib@localhost:5432/axlib_test pytest
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://axlib:axlib@localhost:5432/axlib_test"
)
os.environ["STATIC_DIR"] = "/nonexistent"

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import current_user  # noqa: E402
from app.auth_oidc import upsert_user  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _db(tmp_path):
    from app import auth_local

    auth_local._failures.clear()
    settings.upload_dir = tmp_path / "uploads"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()


def make_user(db, ext_id: str, name: str, dept: str = "AX팀"):
    user = upsert_user(db, {"sub": ext_id, "name": name, "department": dept})
    db.commit()
    return user


@pytest.fixture
def login(db):
    """login('u1', '홍길동') → 이후 요청은 그 사용자로 처리됩니다. SSO 왕복은 건너뜁니다."""
    def _login(ext_id: str = "u1", name: str = "홍길동", dept: str = "AX팀"):
        user = make_user(db, ext_id, name, dept)
        app.dependency_overrides[current_user] = lambda: user
        return user
    return _login


@pytest.fixture
def client():
    return TestClient(app)
