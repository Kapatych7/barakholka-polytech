from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _authenticate(db: DbSession, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> User:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует")
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: DbSession) -> Token:
    """Вход для мобильного клиента (JSON)."""
    user = _authenticate(db, data.email, data.password)
    return Token(access_token=create_access_token(user.id))


@router.post("/token", response_model=Token, include_in_schema=False)
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Вход через форму — нужен для кнопки Authorize в Swagger UI."""
    user = _authenticate(db, form.username, form.password)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
