from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import AuthResponse, UserCreate, UserLogin, UserShort

router = APIRouter(prefix="/auth", tags=["Авторизация"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(user=UserShort.model_validate(user), access_token=create_access_token(user.id))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> AuthResponse:
    """Регистрация (3.1.1). Сразу возвращает токен; роль всегда user."""
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError(409, "EMAIL_ALREADY_EXISTS", "Почта уже зарегистрирована")
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin, db: DbSession) -> AuthResponse:
    """Вход по email и паролю (3.1.2)."""
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Неверный email или пароль")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_BLOCKED", "Аккаунт заблокирован")
    return _auth_response(user)
