"""Схемы запросов и ответов строго по контракту API (Rest_api_mvp)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, StringConstraints


def _iso_utc(value: datetime) -> str:
    # В БД время хранится в UTC без зоны; отдаём ISO 8601 с суффиксом Z (контракт, 2.5)
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat() + "Z"


def _price_str(value: Decimal) -> str:
    # Цена — строка с двумя знаками после точки (контракт, 2.6)
    return f"{Decimal(value):.2f}"


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]
PriceOut = Annotated[Decimal, PlainSerializer(_price_str, return_type=str)]
PriceIn = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2, examples=["1200.00"])]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Общие ----------


class Pagination(BaseModel):
    limit: int
    offset: int
    total: int


# ---------- Пользователи и авторизация ----------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserShort(ORMModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str


class AuthResponse(BaseModel):
    user: UserShort
    access_token: str
    token_type: str = "Bearer"


class UserProfile(ORMModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: UtcDatetime
    is_active: bool
    role: str


class PersonOut(ORMModel):
    id: int
    first_name: str
    last_name: str


# ---------- Справочники ----------


class CategoryOut(ORMModel):
    id: int
    name: str


class CategoryList(BaseModel):
    items: list[CategoryOut]


class LocationOut(ORMModel):
    id: int
    name: str
    location_type: str
    address: str


class LocationList(BaseModel):
    items: list[LocationOut]


# ---------- Объявления ----------


class AdCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int
    location_id: int
    title: Title
    description: NonEmptyStr
    price: PriceIn


class AdUpdate(BaseModel):
    """PATCH: меняются только переданные поля; status здесь менять нельзя (422)."""

    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    location_id: int | None = None
    title: Title | None = None
    description: NonEmptyStr | None = None
    price: PriceIn | None = None


class AdOut(ORMModel):
    """Ответ на создание и редактирование (3.7.1, 3.7.2)."""

    id: int
    user_id: int
    category_id: int
    location_id: int
    title: str
    description: str
    price: PriceOut
    status: str
    created_at: UtcDatetime
    updated_at: UtcDatetime


class AdFeedItem(BaseModel):
    """Карточка в ленте (3.2.1)."""

    id: int
    user_id: int
    category_id: int
    location_id: int
    title: str
    price: PriceOut
    status: str
    main_image_url: str | None
    created_at: UtcDatetime


class AdFeedPage(BaseModel):
    items: list[AdFeedItem]
    pagination: Pagination


class MyAdItem(BaseModel):
    """Карточка в «Моих объявлениях» (3.4.2)."""

    id: int
    title: str
    price: PriceOut
    status: str
    location_id: int
    main_image_url: str | None
    created_at: UtcDatetime


class MyAdPage(BaseModel):
    items: list[MyAdItem]
    pagination: Pagination


class AdImageOut(ORMModel):
    id: int
    image_url: str
    is_main: bool


class AdDetail(ORMModel):
    """Детальный экран объявления (3.5.1)."""

    id: int
    user_id: int
    category_id: int
    location_id: int
    title: str
    description: str
    price: PriceOut
    status: str
    seller: PersonOut
    category: CategoryOut
    location: LocationOut
    images: list[AdImageOut]
    created_at: UtcDatetime
    updated_at: UtcDatetime


class AdStatusOut(ORMModel):
    """Ответ на close / reopen / archive (3.7.6–3.7.8)."""

    id: int
    status: str
    updated_at: UtcDatetime
