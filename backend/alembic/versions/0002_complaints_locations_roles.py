"""Правки структуры БД по задаче #2: роли, места встречи, статус hidden, жалобы, прочтение сообщений

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Начальное наполнение справочника мест встречи (документ «Структура БД», раздел 7)
LOCATIONS = [
    (1, "Общежитие № 1", "dormitory", "г. Москва, ул. Малая Семёновская, д. 12"),
    (2, "Общежитие № 2", "dormitory", "г. Москва, ул. 7-я Парковая, д. 9/26"),
    (3, "Общежитие № 3", "dormitory", "г. Москва, ул. 1-я Дубровская, д. 16А, стр. 2"),
    (4, "Общежитие № 4", "dormitory", "г. Москва, ул. 800-летия Москвы, д. 28, к. 1"),
    (5, "Общежитие № 5", "dormitory", "г. Москва, ул. Михалковская, д. 7, к. 3"),
    (6, "Общежитие № 6", "dormitory", "г. Москва, ул. Бориса Галушкина, д. 9"),
    (7, "Общежитие № 7", "dormitory", "г. Москва, ул. Павла Корчагина, д. 20А, к. 3"),
    (8, "Общежитие № 8", "dormitory", "г. Москва, Рижский проезд, д. 15, к. 2"),
    (9, "Общежитие № 9", "dormitory", "г. Москва, Рижский проезд, д. 15, к. 1"),
    (10, "Общежитие № 10", "dormitory", "г. Москва, 1-й Балтийский переулок, д. 6/21, к. 3"),
    (11, "Общежитие № 11", "dormitory", "г. Москва, ул. Павла Корчагина, д. 22А, к. 2"),
    (12, "Учебный корпус на Автозаводской", "academic_building", "г. Москва, ул. Автозаводская, д. 16"),
    (13, "Большая Семёновская (главный кампус)", "academic_building", "ул. Большая Семёновская, д. 38"),
    (14, "Павла Корчагина", "academic_building", "ул. Павла Корчагина, д. 22"),
    (15, "Прянишникова", "academic_building", "ул. Прянишникова, д. 2А"),
    (16, "Михалковская", "academic_building", "ул. Михалковская, д. 7"),
]
DEFAULT_LOCATION_ID = 13  # для объявлений, созданных до появления location_id


def upgrade() -> None:
    # 1. Users.role
    op.add_column(
        "users", sa.Column("role", sa.String(length=20), server_default="user", nullable=False)
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'moderator', 'admin')")

    # 2. Locations + наполнение
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location_type", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "location_type IN ('dormitory', 'academic_building')", name="ck_locations_type"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    locations = sa.table(
        "locations",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("location_type", sa.String),
        sa.column("address", sa.String),
    )
    op.bulk_insert(
        locations,
        [{"id": i, "name": n, "location_type": t, "address": a} for i, n, t, a in LOCATIONS],
    )
    # id заданы явно — сдвигаем счётчик, чтобы новые записи получали id после 16
    op.execute("SELECT setval(pg_get_serial_sequence('locations', 'id'), (SELECT MAX(id) FROM locations))")

    # 3. Advertisements: location_id (NOT NULL), статус hidden, DEFAULT 'active'
    op.add_column("advertisements", sa.Column("location_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE advertisements SET location_id = {DEFAULT_LOCATION_ID} WHERE location_id IS NULL")
    op.alter_column("advertisements", "location_id", nullable=False)
    op.create_foreign_key(
        "fk_advertisements_location_id",
        "advertisements",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_advertisements_status", "advertisements", type_="check")
    op.create_check_constraint(
        "ck_advertisements_status",
        "advertisements",
        "status IN ('active', 'closed', 'archived', 'hidden')",
    )
    op.alter_column("advertisements", "status", server_default="active")

    # 4. Messages.is_read
    op.add_column(
        "messages", sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False)
    )

    # 5. Complaints
    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=False),
        sa.Column("moderator_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="new", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "reason IN ('spam', 'fraud', 'prohibited_item', 'wrong_category', 'other')",
            name="ck_complaints_reason",
        ),
        sa.CheckConstraint(
            "status IN ('new', 'in_review', 'accepted', 'rejected')", name="ck_complaints_status"
        ),
        sa.CheckConstraint(
            "(status = 'new' AND moderator_id IS NULL) OR "
            "(status IN ('in_review', 'accepted', 'rejected') AND moderator_id IS NOT NULL)",
            name="ck_complaints_moderator_consistency",
        ),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ad_id"], ["advertisements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["moderator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reporter_id", "ad_id", name="uq_complaints_reporter_ad"),
    )
    # Функция set_updated_at() создана в миграции 0001
    op.execute(
        """
        CREATE TRIGGER trg_complaints_updated_at
        BEFORE UPDATE ON complaints
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_complaints_updated_at ON complaints")
    op.drop_table("complaints")

    op.drop_column("messages", "is_read")

    op.execute("UPDATE advertisements SET status = 'closed' WHERE status = 'hidden'")
    op.alter_column("advertisements", "status", server_default=None)
    op.drop_constraint("ck_advertisements_status", "advertisements", type_="check")
    op.create_check_constraint(
        "ck_advertisements_status", "advertisements", "status IN ('active', 'closed', 'archived')"
    )
    op.drop_constraint("fk_advertisements_location_id", "advertisements", type_="foreignkey")
    op.drop_column("advertisements", "location_id")

    op.drop_table("locations")

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
