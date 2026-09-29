"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-29
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('categories',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('advertisements',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'closed', 'archived')", name='ck_advertisements_status'),
    sa.CheckConstraint('price >= 0', name='ck_advertisements_price_non_negative'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ad_images',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('ad_id', sa.Integer(), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=False),
    sa.Column('is_main', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['ad_id'], ['advertisements.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chats',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('ad_id', sa.Integer(), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['ad_id'], ['advertisements.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ad_id', 'buyer_id', name='uq_chats_ad_buyer')
    )
    op.create_table('messages',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
    sa.Column('chat_id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    # Триггер updated_at — из документа «Структура БД», раздел 3
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_ads_updated_at
        BEFORE UPDATE ON advertisements
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # Стартовый справочник категорий
    categories = sa.table("categories", sa.column("name", sa.String))
    op.bulk_insert(
        categories,
        [{"name": n} for n in ("Учебники", "Техника", "Одежда", "Услуги", "Другое")],
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_ads_updated_at ON advertisements")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('ad_images')
    op.drop_table('advertisements')
    op.drop_table('users')
    op.drop_table('categories')
