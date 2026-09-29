from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.routes import auth, categories
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)
api.include_router(categories.router)


@api.get("/health", tags=["system"])
def health(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(api)
