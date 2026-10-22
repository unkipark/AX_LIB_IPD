"""마이그레이션 실행 환경. DB 주소는 앱과 같은 DATABASE_URL 을 씁니다."""
from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401 — 테이블 메타데이터 등록
from app.db import Base, engine

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
