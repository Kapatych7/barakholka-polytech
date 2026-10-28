"""Тесты гоняются на настоящем PostgreSQL (как в проде).

Локально: `docker compose -f infra/docker-compose.yml up -d db`, затем `pytest` из папки backend.
База берётся из DATABASE_URL (см. .env.example).
"""

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.db.session import engine
from app.main import app

_counter = itertools.count(1)


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE users, advertisements, ad_images, chats, messages, complaints "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, **overrides) -> dict:
    n = next(_counter)
    payload = {
        "email": f"student{n}@mospolytech.ru",
        "password": "supersecret1",
        "first_name": "Иван",
        "last_name": f"Иванов{n}",
    } | overrides
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def user(client) -> dict:
    """Зарегистрированный пользователь: {"user": ..., "access_token": ..., "headers": ...}."""
    data = register(client)
    data["headers"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data


@pytest.fixture
def other_user(client) -> dict:
    data = register(client)
    data["headers"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data


AD = {
    "category_id": 1,
    "location_id": 1,
    "title": "Продам учебник по программированию",
    "description": "Учебник в хорошем состоянии.",
    "price": "1200.00",
}


def create_ad(client: TestClient, headers: dict, **overrides) -> dict:
    r = client.post("/api/v1/ads", json=AD | overrides, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
