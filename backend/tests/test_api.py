USER = {
    "email": "Student@mospolytech.ru",
    "password": "supersecret1",
    "first_name": "Иван",
    "last_name": "Иванов",
}


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_categories_seeded(client):
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    assert {c["name"] for c in r.json()} >= {"Учебники", "Техника", "Одежда", "Услуги"}


def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json=USER)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "student@mospolytech.ru"
    assert "password_hash" not in r.json()

    r = client.post("/api/v1/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["first_name"] == "Иван"


def test_register_duplicate_email(client):
    assert client.post("/api/v1/auth/register", json=USER).status_code == 201
    assert client.post("/api/v1/auth/register", json=USER).status_code == 409


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json=USER)
    r = client.post("/api/v1/auth/login", json={"email": USER["email"], "password": "wrong-pass"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
