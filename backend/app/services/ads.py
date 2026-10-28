"""Бизнес-логика объявлений: видимость, владение и переходы статусов (Структура БД, раздел 9)."""

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import AdImage, Advertisement, Category, Location, User

# Разрешённые автору переходы: действие -> (из каких статусов, в какой)
AUTHOR_TRANSITIONS: dict[str, tuple[set[str], str]] = {
    "close": ({"active"}, "closed"),
    "reopen": ({"closed"}, "active"),
    "archive": ({"active", "closed"}, "archived"),
}
EDITABLE_STATUSES = {"active", "closed"}


def main_image_url_column():
    """Ссылка на главное фото объявления (или NULL) для списков."""
    return (
        select(AdImage.image_url)
        .where(AdImage.ad_id == Advertisement.id, AdImage.is_main.is_(True))
        .order_by(AdImage.id)
        .limit(1)
        .correlate(Advertisement)
        .scalar_subquery()
        .label("main_image_url")
    )


def count_and_page(db: Session, query: Select, limit: int, offset: int) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.execute(query.limit(limit).offset(offset)).all()
    return rows, total


def get_ad_for_viewer(db: Session, ad_id: int, viewer: User) -> Advertisement:
    """Автор видит своё объявление в любом статусе, остальные — только active; иначе 404."""
    ad = db.scalar(
        select(Advertisement)
        .where(Advertisement.id == ad_id)
        .options(
            selectinload(Advertisement.seller),
            selectinload(Advertisement.category),
            selectinload(Advertisement.location),
            selectinload(Advertisement.images),
        )
    )
    if ad is None or (ad.status != "active" and ad.user_id != viewer.id):
        raise AppError(404, "AD_NOT_FOUND", "Объявление не найдено")
    return ad


def get_own_ad(db: Session, ad_id: int, user: User, *, lock: bool = False) -> Advertisement:
    query = select(Advertisement).where(Advertisement.id == ad_id)
    if lock:
        query = query.with_for_update()
    ad = db.scalar(query)
    if ad is None:
        raise AppError(404, "AD_NOT_FOUND", "Объявление не найдено")
    if ad.user_id != user.id:
        raise AppError(403, "NOT_AD_OWNER", "Объявление принадлежит другому пользователю")
    return ad


def ensure_category(db: Session, category_id: int) -> None:
    if db.get(Category, category_id) is None:
        raise AppError(404, "CATEGORY_NOT_FOUND", "Категория не найдена", {"category_id": category_id})


def ensure_location(db: Session, location_id: int) -> None:
    if db.get(Location, location_id) is None:
        raise AppError(
            404,
            "LOCATION_NOT_FOUND",
            "Место встречи не найдено в справочнике",
            {"location_id": location_id},
        )


def change_status(db: Session, ad: Advertisement, action: str) -> Advertisement:
    allowed_from, target = AUTHOR_TRANSITIONS[action]
    if ad.status not in allowed_from:
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            f"Переход из статуса «{ad.status}» в «{target}» запрещён",
            {"current_status": ad.status, "target_status": target},
        )
    ad.status = target
    db.commit()
    db.refresh(ad)  # updated_at выставляет триггер в БД
    return ad
