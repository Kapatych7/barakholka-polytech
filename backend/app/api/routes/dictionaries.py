"""Справочники: категории (3.2.2) и места встречи (3.2.3)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Category, Location
from app.schemas import CategoryList, LocationList

router = APIRouter(tags=["Справочники"])


@router.get("/categories", response_model=CategoryList)
def list_categories(db: DbSession, _: CurrentUser) -> dict:
    return {"items": list(db.scalars(select(Category).order_by(Category.id)))}


@router.get("/locations", response_model=LocationList)
def list_locations(db: DbSession, _: CurrentUser) -> dict:
    return {"items": list(db.scalars(select(Location).order_by(Location.id)))}
