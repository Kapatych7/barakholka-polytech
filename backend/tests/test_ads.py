"""Тесты задачи #5 «CRUD объявлений»."""

from sqlalchemy import update

from app.db.session import engine
from app.models import AdImage, Advertisement
from tests.conftest import AD, create_ad
from tests.test_auth import assert_error


def feed(client, headers, **params):
    r = client.get("/api/v1/ads", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def feed_ids(client, headers, **params):
    return [item["id"] for item in feed(client, headers, **params)["items"]]


# ---------- Создание и лента ----------


def test_create_ad_and_it_appears_in_feed(client, user, other_user):
    ad = create_ad(client, user["headers"])
    assert ad["status"] == "active"
    assert ad["user_id"] == user["user"]["id"]
    assert ad["price"] == "1200.00"
    assert ad["created_at"].endswith("Z") and ad["updated_at"].endswith("Z")
    assert set(ad) == {
        "id", "user_id", "category_id", "location_id", "title", "description",
        "price", "status", "created_at", "updated_at",
    }  # fmt: skip

    body = feed(client, other_user["headers"])
    assert body["pagination"] == {"limit": 20, "offset": 0, "total": 1}
    item = body["items"][0]
    assert item["id"] == ad["id"]
    assert item["main_image_url"] is None
    assert set(item) == {
        "id", "user_id", "category_id", "location_id", "title", "price",
        "status", "main_image_url", "created_at",
    }  # fmt: skip


def test_create_ad_price_formats(client, user):
    assert create_ad(client, user["headers"], price=0)["price"] == "0.00"
    assert create_ad(client, user["headers"], price="99.5")["price"] == "99.50"
    assert create_ad(client, user["headers"], price=150)["price"] == "150.00"


def test_create_ad_validation(client, user):
    h = user["headers"]
    for bad in [
        {"title": "   "},
        {"price": "-1"},
        {"price": "1.234"},
        {"description": ""},
        {"status": "closed"},
    ]:
        r = client.post("/api/v1/ads", json=AD | bad, headers=h)
        assert_error(r, 422, "VALIDATION_ERROR")
    r = client.post("/api/v1/ads", json=AD | {"category_id": 999}, headers=h)
    assert_error(r, 404, "CATEGORY_NOT_FOUND")
    r = client.post("/api/v1/ads", json=AD | {"location_id": 999}, headers=h)
    assert_error(r, 404, "LOCATION_NOT_FOUND")


def test_main_image_url_in_lists(client, user):
    ad = create_ad(client, user["headers"])
    with engine.begin() as conn:
        conn.execute(
            AdImage.__table__.insert(),
            [
                {"ad_id": ad["id"], "image_url": "https://example.com/a.jpg", "is_main": False},
                {"ad_id": ad["id"], "image_url": "https://example.com/main.jpg", "is_main": True},
            ],
        )
    assert feed(client, user["headers"])["items"][0]["main_image_url"] == "https://example.com/main.jpg"
    my = client.get("/api/v1/users/me/ads", headers=user["headers"]).json()
    assert my["items"][0]["main_image_url"] == "https://example.com/main.jpg"
    detail = client.get(f"/api/v1/ads/{ad['id']}", headers=user["headers"]).json()
    assert [i["is_main"] for i in detail["images"]] == [False, True]


# ---------- Карточка ----------


def test_ad_detail(client, user, other_user):
    ad = create_ad(client, user["headers"], category_id=2, location_id=12)
    r = client.get(f"/api/v1/ads/{ad['id']}", headers=other_user["headers"])
    assert r.status_code == 200
    d = r.json()
    assert d["seller"] == {
        "id": user["user"]["id"],
        "first_name": user["user"]["first_name"],
        "last_name": user["user"]["last_name"],
    }
    assert d["category"] == {"id": 2, "name": "Техника"}
    assert d["location"]["id"] == 12 and d["location"]["location_type"] == "academic_building"
    assert d["images"] == []
    assert d["description"] == AD["description"]


def test_ad_detail_not_found(client, user):
    assert_error(client.get("/api/v1/ads/12345", headers=user["headers"]), 404, "AD_NOT_FOUND")


def test_closed_ad_visible_only_to_author(client, user, other_user):
    ad = create_ad(client, user["headers"])
    client.post(f"/api/v1/ads/{ad['id']}/close", headers=user["headers"])
    assert client.get(f"/api/v1/ads/{ad['id']}", headers=user["headers"]).status_code == 200
    assert_error(client.get(f"/api/v1/ads/{ad['id']}", headers=other_user["headers"]), 404, "AD_NOT_FOUND")


# ---------- Редактирование ----------


def test_edit_own_ad(client, user):
    ad = create_ad(client, user["headers"])
    r = client.patch(
        f"/api/v1/ads/{ad['id']}",
        json={"title": "Продам учебник Python", "price": "1000.00", "location_id": 3},
        headers=user["headers"],
    )
    assert r.status_code == 200, r.text
    upd = r.json()
    assert upd["title"] == "Продам учебник Python"
    assert upd["price"] == "1000.00"
    assert upd["location_id"] == 3
    assert upd["description"] == AD["description"]  # не переданное поле не меняется
    assert upd["updated_at"] >= ad["updated_at"]


def test_edit_closed_ad_allowed(client, user):
    ad = create_ad(client, user["headers"])
    client.post(f"/api/v1/ads/{ad['id']}/close", headers=user["headers"])
    r = client.patch(f"/api/v1/ads/{ad['id']}", json={"price": "500"}, headers=user["headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


def test_cannot_edit_someone_elses_ad(client, user, other_user):
    ad = create_ad(client, user["headers"])
    r = client.patch(f"/api/v1/ads/{ad['id']}", json={"title": "Чужое"}, headers=other_user["headers"])
    assert_error(r, 403, "NOT_AD_OWNER")
    for action in ("close", "reopen", "archive"):
        r = client.post(f"/api/v1/ads/{ad['id']}/{action}", headers=other_user["headers"])
        assert_error(r, 403, "NOT_AD_OWNER")
    detail = client.get(f"/api/v1/ads/{ad['id']}", headers=user["headers"]).json()
    assert detail["title"] == AD["title"] and detail["status"] == "active"


def test_edit_errors(client, user):
    ad = create_ad(client, user["headers"])
    url = f"/api/v1/ads/{ad['id']}"
    assert_error(
        client.patch(url, json={"status": "closed"}, headers=user["headers"]), 422, "VALIDATION_ERROR"
    )
    assert_error(client.patch(url, json={"title": None}, headers=user["headers"]), 422, "VALIDATION_ERROR")
    assert_error(client.patch(url, json={"price": "-5"}, headers=user["headers"]), 422, "VALIDATION_ERROR")
    assert_error(
        client.patch(url, json={"category_id": 999}, headers=user["headers"]), 404, "CATEGORY_NOT_FOUND"
    )
    assert_error(
        client.patch(url, json={"location_id": 999}, headers=user["headers"]), 404, "LOCATION_NOT_FOUND"
    )
    assert_error(
        client.patch("/api/v1/ads/9999", json={"title": "x"}, headers=user["headers"]), 404, "AD_NOT_FOUND"
    )


def test_archived_and_hidden_not_editable(client, user):
    archived = create_ad(client, user["headers"])
    client.post(f"/api/v1/ads/{archived['id']}/archive", headers=user["headers"])
    hidden = create_ad(client, user["headers"])
    with engine.begin() as conn:
        conn.execute(update(Advertisement).where(Advertisement.id == hidden["id"]).values(status="hidden"))
    for ad in (archived, hidden):
        r = client.patch(f"/api/v1/ads/{ad['id']}", json={"title": "x"}, headers=user["headers"])
        assert_error(r, 409, "AD_NOT_EDITABLE")


# ---------- Смена статуса ----------


def test_status_transitions(client, user):
    ad = create_ad(client, user["headers"])
    url = f"/api/v1/ads/{ad['id']}"
    h = user["headers"]

    r = client.post(f"{url}/close", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "closed"
    assert set(r.json()) == {"id", "status", "updated_at"}
    assert_error(client.post(f"{url}/close", headers=h), 409, "INVALID_STATUS_TRANSITION")

    r = client.post(f"{url}/reopen", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert_error(client.post(f"{url}/reopen", headers=h), 409, "INVALID_STATUS_TRANSITION")

    r = client.post(f"{url}/archive", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "archived"
    for action in ("close", "reopen", "archive"):
        assert_error(client.post(f"{url}/{action}", headers=h), 409, "INVALID_STATUS_TRANSITION")


def test_closed_to_archived(client, user):
    ad = create_ad(client, user["headers"])
    client.post(f"/api/v1/ads/{ad['id']}/close", headers=user["headers"])
    r = client.post(f"/api/v1/ads/{ad['id']}/archive", headers=user["headers"])
    assert r.json()["status"] == "archived"


def test_author_cannot_unhide(client, user):
    ad = create_ad(client, user["headers"])
    with engine.begin() as conn:
        conn.execute(update(Advertisement).where(Advertisement.id == ad["id"]).values(status="hidden"))
    for action in ("close", "reopen", "archive"):
        r = client.post(f"/api/v1/ads/{ad['id']}/{action}", headers=user["headers"])
        assert_error(r, 409, "INVALID_STATUS_TRANSITION")


def test_status_action_not_found(client, user):
    assert_error(client.post("/api/v1/ads/9999/close", headers=user["headers"]), 404, "AD_NOT_FOUND")


def test_closed_ad_not_in_feed_but_in_my_ads(client, user, other_user):
    active = create_ad(client, user["headers"], title="Активное")
    closed = create_ad(client, user["headers"], title="Закрытое")
    archived = create_ad(client, user["headers"], title="Архивное")
    client.post(f"/api/v1/ads/{closed['id']}/close", headers=user["headers"])
    client.post(f"/api/v1/ads/{archived['id']}/archive", headers=user["headers"])

    for h in (user["headers"], other_user["headers"]):
        assert feed_ids(client, h) == [active["id"]]

    r = client.get("/api/v1/users/me/ads", headers=user["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 3
    assert {i["id"]: i["status"] for i in body["items"]} == {
        active["id"]: "active",
        closed["id"]: "closed",
        archived["id"]: "archived",
    }
    r = client.get("/api/v1/users/me/ads", params={"status": "closed"}, headers=user["headers"])
    assert [i["id"] for i in r.json()["items"]] == [closed["id"]]
    assert client.get("/api/v1/users/me/ads", headers=other_user["headers"]).json()["items"] == []


def test_my_ads_invalid_status(client, user):
    r = client.get("/api/v1/users/me/ads", params={"status": "deleted"}, headers=user["headers"])
    assert_error(r, 422, "INVALID_STATUS")


# ---------- Фильтры, сортировка, пагинация ----------


def _seed(client, headers):
    def ad(**kw):
        return create_ad(client, headers, **({"description": "Состояние хорошее"} | kw))

    return {
        "book": ad(title="Учебник по матанализу", category_id=1, location_id=1, price="300"),
        "laptop": ad(
            title="Ноутбук",
            description="Почти новый, 100% рабочий",
            category_id=2,
            location_id=2,
            price="25000",
        ),
        "coat": ad(title="Халат для лабораторных", category_id=3, location_id=1, price="0"),
        "lamp": ad(title="Настольная лампа", category_id=2, location_id=12, price="300"),
    }


def test_filter_by_category(client, user):
    ads = _seed(client, user["headers"])
    assert sorted(feed_ids(client, user["headers"], category_id=2)) == sorted(
        [ads["laptop"]["id"], ads["lamp"]["id"]]
    )


def test_filter_by_location(client, user):
    ads = _seed(client, user["headers"])
    assert sorted(feed_ids(client, user["headers"], location_id=1)) == sorted(
        [ads["book"]["id"], ads["coat"]["id"]]
    )


def test_filter_by_price(client, user):
    ads = _seed(client, user["headers"])
    h = user["headers"]
    assert sorted(feed_ids(client, h, min_price="300", max_price="1000")) == sorted(
        [ads["book"]["id"], ads["lamp"]["id"]]
    )
    assert feed_ids(client, h, max_price="0") == [ads["coat"]["id"]]
    assert feed_ids(client, h, min_price="20000") == [ads["laptop"]["id"]]


def test_search(client, user):
    ads = _seed(client, user["headers"])
    h = user["headers"]
    assert feed_ids(client, h, q="учебник") == [ads["book"]["id"]]  # без учёта регистра
    assert feed_ids(client, h, q="почти новый") == [ads["laptop"]["id"]]  # по описанию
    assert feed_ids(client, h, q="100%") == [ads["laptop"]["id"]]  # спецсимволы не ломают поиск
    assert feed_ids(client, h, q="велосипед") == []


def test_combined_filters(client, user):
    ads = _seed(client, user["headers"])
    assert feed_ids(client, user["headers"], category_id=2, location_id=12, max_price="500") == [
        ads["lamp"]["id"]
    ]


def test_sorting(client, user):
    ads = _seed(client, user["headers"])
    h = user["headers"]
    newest_first = [ads[k]["id"] for k in ("lamp", "coat", "laptop", "book")]
    assert feed_ids(client, h) == newest_first
    assert feed_ids(client, h, sort="created_at_desc") == newest_first
    # при равной цене (book и lamp по 300) — сначала новые
    assert feed_ids(client, h, sort="price_asc") == [ads[k]["id"] for k in ("coat", "lamp", "book", "laptop")]
    assert feed_ids(client, h, sort="price_desc") == [
        ads[k]["id"] for k in ("laptop", "lamp", "book", "coat")
    ]


def test_pagination(client, user):
    ids = [create_ad(client, user["headers"], title=f"Объявление {i}")["id"] for i in range(5)]
    newest_first = ids[::-1]
    h = user["headers"]
    page1 = feed(client, h, limit=2, offset=0)
    assert page1["pagination"] == {"limit": 2, "offset": 0, "total": 5}
    assert [i["id"] for i in page1["items"]] == newest_first[:2]
    assert feed_ids(client, h, limit=2, offset=2) == newest_first[2:4]
    assert feed_ids(client, h, limit=2, offset=4) == newest_first[4:]
    assert feed(client, h, limit=2, offset=10)["items"] == []
    # total учитывает фильтры
    assert feed(client, h, q="Объявление 1", limit=1)["pagination"]["total"] == 1


def test_invalid_filters(client, user):
    h = user["headers"]
    for params in [
        {"min_price": "-1"},
        {"min_price": "500", "max_price": "100"},
        {"min_price": "abc"},
        {"category_id": "x"},
    ]:
        assert_error(client.get("/api/v1/ads", params=params, headers=h), 422, "INVALID_FILTER")
    assert_error(client.get("/api/v1/ads", params={"sort": "random"}, headers=h), 422, "INVALID_SORT")
    for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}]:
        assert_error(client.get("/api/v1/ads", params=params, headers=h), 422, "VALIDATION_ERROR")
