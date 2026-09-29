from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Category
from app.schemas import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))
