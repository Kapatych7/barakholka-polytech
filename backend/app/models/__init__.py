"""ORM-модели по утверждённому документу «Структура БД Барахолка Политех»."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


AD_STATUSES = ("active", "closed", "archived")


class Advertisement(Base):
    __tablename__ = "advertisements"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_advertisements_price_non_negative"),
        CheckConstraint("status IN ('active', 'closed', 'archived')", name="ck_advertisements_status"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    images: Mapped[list["AdImage"]] = relationship(
        back_populates="ad", cascade="all, delete-orphan", passive_deletes=True
    )


class AdImage(Base):
    __tablename__ = "ad_images"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    ad: Mapped[Advertisement] = relationship(back_populates="images")


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (UniqueConstraint("ad_id", "buyer_id", name="uq_chats_ad_buyer"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
