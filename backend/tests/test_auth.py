from sqlalchemy import update

from app.db.session import engine
from app.models import User
from tests.conftest import register


def assert_error(r, status: int, code: str):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], dict)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_register_returns_user_and_token(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Student@Example.com",
            "password": "SecurePass123",
            "first_name": "Иван",
            "last_name": "Иванов",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "student@example.com"
    assert set(body["user"]) == {"id", "email", "first_name", "last_name"}
    assert body["token_type"] == "Bearer"
    assert body["access_token"]


def test_register_duplicate_email(client):
    register(client, email="dup@example.com")
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "SecurePass123", "first_name": "A", "last_name": "B"},
    )
    assert_error(r, 409, "EMAIL_ALREADY_EXISTS")


def test_register_short_password(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "short", "first_name": "A", "last_name": "B"},
    )
    assert_error(r, 422, "VALIDATION_ERROR")
    assert r.json()["error"]["details"]["field"] == "password"
    assert r.json()["error"]["details"]["min_length"] == 8


def test_login_and_profile(client):
    reg = register(client, email="login@example.com", password="SecurePass123")
    r = client.post("/api/v1/auth/login", json={"email": "LOGIN@example.com", "password": "SecurePass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["user"]["id"] == reg["user"]["id"]

    r = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()
    assert me["role"] == "user"
    assert me["is_active"] is True
    assert me["created_at"].endswith("Z")
    assert "password_hash" not in me


def test_login_wrong_password(client):
    register(client, email="x@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"})
    assert_error(r, 401, "INVALID_CREDENTIALS")


def test_blocked_account(client):
    reg = register(client, email="blocked@example.com", password="SecurePass123")
    with engine.begin() as conn:
        conn.execute(update(User).where(User.id == reg["user"]["id"]).values(is_active=False))
    r = client.post("/api/v1/auth/login", json={"email": "blocked@example.com", "password": "SecurePass123"})
    assert_error(r, 403, "ACCOUNT_BLOCKED")
    r = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {reg['access_token']}"})
    assert_error(r, 403, "ACCOUNT_BLOCKED")


def test_requests_without_token(client):
    for method, path in [
        ("get", "/api/v1/users/me"),
        ("get", "/api/v1/users/me/ads"),
        ("get", "/api/v1/categories"),
        ("get", "/api/v1/locations"),
        ("get", "/api/v1/ads"),
        ("get", "/api/v1/ads/1"),
        ("post", "/api/v1/ads"),
        ("patch", "/api/v1/ads/1"),
        ("post", "/api/v1/ads/1/close"),
        ("post", "/api/v1/ads/1/reopen"),
        ("post", "/api/v1/ads/1/archive"),
    ]:
        r = getattr(client, method)(path)
        assert_error(r, 401, "UNAUTHORIZED")


def test_invalid_token(client):
    r = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert_error(r, 401, "UNAUTHORIZED")


def test_dictionaries(client, user):
    r = client.get("/api/v1/categories", headers=user["headers"])
    assert r.status_code == 200
    names = [c["name"] for c in r.json()["items"]]
    assert {"Учебники", "Техника", "Одежда", "Услуги"} <= set(names)

    r = client.get("/api/v1/locations", headers=user["headers"])
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 16
    assert items[0] == {
        "id": 1,
        "name": "Общежитие № 1",
        "location_type": "dormitory",
        "address": "г. Москва, ул. Малая Семёновская, д. 12",
    }
    assert sum(i["location_type"] == "dormitory" for i in items) == 11
