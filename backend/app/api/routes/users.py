"""Профиль пользователя (контракт 3.4)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.models import AD_STATUSES, Advertisement, User
from app.schemas import MyAdPage, UserProfile
from app.services import ads as svc

router = APIRouter(prefix="/users", tags=["Профиль"])


@router.get("/me", response_model=UserProfile, summary="Мой профиль")
def me(user: CurrentUser) -> User:
    return user


@router.get("/me/ads", response_model=MyAdPage, summary="Мои объявления (все статусы)")
def my_ads(
    db: DbSession,
    user: CurrentUser,
    status: Annotated[str | None, Query(description="active | closed | archived | hidden")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    if status is not None and status not in AD_STATUSES:
        raise AppError(422, "INVALID_STATUS", "Неизвестный статус", {"allowed": list(AD_STATUSES)})
    query = select(Advertisement, svc.main_image_url_column()).where(Advertisement.user_id == user.id)
    if status is not None:
        query = query.where(Advertisement.status == status)
    query = query.order_by(Advertisement.created_at.desc(), Advertisement.id.desc())
    rows, total = svc.count_and_page(db, query, limit, offset)
    items = [
        {
            "id": ad.id,
            "title": ad.title,
            "price": ad.price,
            "status": ad.status,
            "location_id": ad.location_id,
            "main_image_url": main_image_url,
            "created_at": ad.created_at,
        }
        for ad, main_image_url in rows
    ]
    return {"items": items, "pagination": {"limit": limit, "offset": offset, "total": total}}
