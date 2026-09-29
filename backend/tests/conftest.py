"""Тесты гоняются на настоящем PostgreSQL (как в проде).

Локально: `docker compose up -d db`, затем `pytest`.
База берётся из DATABASE_URL (см. .env.example).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.db.session import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE users, advertisements, ad_images, chats, messages RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
