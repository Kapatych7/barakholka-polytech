from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# auto_error=False — сами возвращаем 401 в едином формате ошибок
bearer_scheme = HTTPBearer(auto_error=False, description="JWT из /auth/login или /auth/register")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = AppError(401, "UNAUTHORIZED", "Пользователь не авторизован или токен недействителен")
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise AppError(403, "ACCOUNT_BLOCKED", "Аккаунт заблокирован")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
