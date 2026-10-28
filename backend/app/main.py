from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.routes import ads, auth, dictionaries, users
from app.core.config import settings
from app.core.errors import register_error_handlers

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="API мобильного приложения «Барахолка Политех». Контракт: Rest_api_mvp (issue #3).",
)
register_error_handlers(app)

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)
api.include_router(dictionaries.router)
api.include_router(ads.router)
api.include_router(users.router)


@api.get("/health", tags=["Служебное"])
def health(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(api)
