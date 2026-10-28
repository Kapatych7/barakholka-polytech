"""ORM-модели по документу «Структура БД Барахолка Политех» (версия с жалобами и местами встречи)."""

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

USER_ROLES = ("user", "moderator", "admin")
AD_STATUSES = ("active", "closed", "archived", "hidden")
LOCATION_TYPES = ("dormitory", "academic_building")
COMPLAINT_REASONS = ("spam", "fraud", "prohibited_item", "wrong_category", "other")
COMPLAINT_STATUSES = ("new", "in_review", "accepted", "rejected")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(_in("role", USER_ROLES), name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Location(Base):
    """Справочник мест встречи: общежития и учебные корпуса."""

    __tablename__ = "locations"
    __table_args__ = (CheckConstraint(_in("location_type", LOCATION_TYPES), name="ck_locations_type"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)


class Advertisement(Base):
    __tablename__ = "advertisements"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_advertisements_price_non_negative"),
        CheckConstraint(_in("status", AD_STATUSES), name="ck_advertisements_status"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    seller: Mapped[User] = relationship()
    category: Mapped[Category] = relationship()
    location: Mapped[Location] = relationship()
    images: Mapped[list["AdImage"]] = relationship(
        back_populates="ad",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AdImage.id",
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
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class Complaint(Base):
    """Жалоба пользователя на объявление (не больше одной от пользователя на объявление)."""

    __tablename__ = "complaints"
    __table_args__ = (
        UniqueConstraint("reporter_id", "ad_id", name="uq_complaints_reporter_ad"),
        CheckConstraint(_in("reason", COMPLAINT_REASONS), name="ck_complaints_reason"),
        CheckConstraint(_in("status", COMPLAINT_STATUSES), name="ck_complaints_status"),
        CheckConstraint(
            "(status = 'new' AND moderator_id IS NULL) OR "
            "(status IN ('in_review', 'accepted', 'rejected') AND moderator_id IS NOT NULL)",
            name="ck_complaints_moderator_consistency",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    ad_id: Mapped[int] = mapped_column(ForeignKey("advertisements.id", ondelete="RESTRICT"), nullable=False)
    moderator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
