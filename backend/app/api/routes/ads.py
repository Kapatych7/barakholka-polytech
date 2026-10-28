"""Объявления: лента, карточка, создание, редактирование, смена статуса (контракт 3.2.1, 3.5.1, 3.7)."""

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models import Advertisement
from app.schemas import AdCreate, AdDetail, AdFeedPage, AdOut, AdStatusOut, AdUpdate
from app.services import ads as svc

router = APIRouter(prefix="/ads", tags=["Объявления"])

Limit = Annotated[int, Query(ge=1, le=100, description="Количество записей (1–100)")]
Offset = Annotated[int, Query(ge=0, description="Смещение")]

SORTS = {
    "created_at_desc": (Advertisement.created_at.desc(), Advertisement.id.desc()),
    "price_asc": (Advertisement.price.asc(), Advertisement.created_at.desc(), Advertisement.id.desc()),
    "price_desc": (Advertisement.price.desc(), Advertisement.created_at.desc(), Advertisement.id.desc()),
}


def _invalid_filter(field: str, reason: str) -> AppError:
    return AppError(422, "INVALID_FILTER", "Некорректный фильтр", {"field": field, "reason": reason})


def _parse_int(name: str, raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError as e:
        raise _invalid_filter(name, "Ожидается целое число") from e
    if value < 1:
        raise _invalid_filter(name, "Ожидается положительное число")
    return value


def _parse_price(name: str, raw: str | None) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation as e:
        raise _invalid_filter(name, "Ожидается число") from e
    if not value.is_finite() or value < 0:
        raise _invalid_filter(name, "Цена не может быть отрицательной")
    return value


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=AdFeedPage, summary="Лента объявлений с фильтрами")
def feed(
    db: DbSession,
    _: CurrentUser,
    category_id: Annotated[str | None, Query(description="Фильтр по категории")] = None,
    location_id: Annotated[str | None, Query(description="Фильтр по месту встречи")] = None,
    min_price: Annotated[str | None, Query(description="Минимальная цена")] = None,
    max_price: Annotated[str | None, Query(description="Максимальная цена")] = None,
    q: Annotated[str | None, Query(description="Поиск по названию и описанию")] = None,
    sort: Annotated[str, Query(description="created_at_desc | price_asc | price_desc")] = "created_at_desc",
    limit: Limit = 20,
    offset: Offset = 0,
) -> dict:
    """В ленту попадают только объявления со статусом active."""
    cat = _parse_int("category_id", category_id)
    loc = _parse_int("location_id", location_id)
    lo = _parse_price("min_price", min_price)
    hi = _parse_price("max_price", max_price)
    if lo is not None and hi is not None and lo > hi:
        raise _invalid_filter("min_price", "min_price больше max_price")
    if sort not in SORTS:
        raise AppError(422, "INVALID_SORT", "Неизвестное значение sort", {"allowed": list(SORTS)})

    query = select(Advertisement, svc.main_image_url_column()).where(Advertisement.status == "active")
    if cat is not None:
        query = query.where(Advertisement.category_id == cat)
    if loc is not None:
        query = query.where(Advertisement.location_id == loc)
    if lo is not None:
        query = query.where(Advertisement.price >= lo)
    if hi is not None:
        query = query.where(Advertisement.price <= hi)
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        query = query.where(
            or_(
                Advertisement.title.ilike(pattern, escape="\\"),
                Advertisement.description.ilike(pattern, escape="\\"),
            )
        )
    query = query.order_by(*SORTS[sort])

    rows, total = svc.count_and_page(db, query, limit, offset)
    items = [
        {
            "id": ad.id,
            "user_id": ad.user_id,
            "category_id": ad.category_id,
            "location_id": ad.location_id,
            "title": ad.title,
            "price": ad.price,
            "status": ad.status,
            "main_image_url": main_image_url,
            "created_at": ad.created_at,
        }
        for ad, main_image_url in rows
    ]
    return {"items": items, "pagination": {"limit": limit, "offset": offset, "total": total}}


@router.post("", response_model=AdOut, status_code=status.HTTP_201_CREATED, summary="Создание объявления")
def create_ad(data: AdCreate, db: DbSession, user: CurrentUser) -> Advertisement:
    svc.ensure_category(db, data.category_id)
    svc.ensure_location(db, data.location_id)
    ad = Advertisement(user_id=user.id, status="active", **data.model_dump())
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@router.get("/{ad_id}", response_model=AdDetail, summary="Карточка объявления")
def get_ad(ad_id: int, db: DbSession, user: CurrentUser) -> Advertisement:
    """Автор видит своё объявление в любом статусе, остальные — только active."""
    return svc.get_ad_for_viewer(db, ad_id, user)


@router.patch("/{ad_id}", response_model=AdOut, summary="Редактирование объявления")
def update_ad(ad_id: int, data: AdUpdate, db: DbSession, user: CurrentUser) -> Advertisement:
    """Меняются только переданные поля. Статус через этот запрос не меняется."""
    changes = data.model_dump(exclude_unset=True)
    nulls = [k for k, v in changes.items() if v is None]
    if nulls:
        details = {"field": nulls[0], "reason": "Пустое значение"}
        raise AppError(422, "VALIDATION_ERROR", "Данные не прошли проверку", details)
    ad = svc.get_own_ad(db, ad_id, user, lock=True)
    if ad.status not in svc.EDITABLE_STATUSES:
        raise AppError(
            409, "AD_NOT_EDITABLE", "Статус объявления запрещает редактирование", {"status": ad.status}
        )
    if "category_id" in changes:
        svc.ensure_category(db, changes["category_id"])
    if "location_id" in changes:
        svc.ensure_location(db, changes["location_id"])
    for field, value in changes.items():
        setattr(ad, field, value)
    db.commit()
    db.refresh(ad)
    return ad


def _status_action(action: str):
    def handler(ad_id: int, db: DbSession, user: CurrentUser) -> Advertisement:
        ad = svc.get_own_ad(db, ad_id, user, lock=True)
        return svc.change_status(db, ad, action)

    return handler


router.add_api_route(
    "/{ad_id}/close",
    _status_action("close"),
    methods=["POST"],
    response_model=AdStatusOut,
    summary="Закрытие объявления (active → closed)",
)
router.add_api_route(
    "/{ad_id}/reopen",
    _status_action("reopen"),
    methods=["POST"],
    response_model=AdStatusOut,
    summary="Повторное открытие (closed → active)",
)
router.add_api_route(
    "/{ad_id}/archive",
    _status_action("archive"),
    methods=["POST"],
    response_model=AdStatusOut,
    summary="Архивирование (active/closed → archived)",
)
