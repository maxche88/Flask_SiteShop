"""Унифицировать поля name/email в dialogs, убрать guest_*

Revision ID: 304bf5f2c337
Revises: f6fc8098767b
Create Date: 2025-11-19 21:55:30.209326

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '304bf5f2c337'
down_revision = 'f6fc8098767b'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Удаляем старые колонки
    op.drop_column('dialogs', 'guest_name')
    op.drop_column('dialogs', 'guest_email')

    op.execute("DELETE FROM dialogs")
    
    op.add_column('dialogs', sa.Column('name', sa.String(length=100), nullable=False))
    op.add_column('dialogs', sa.Column('email', sa.String(length=120), nullable=False))


def downgrade():
    # Восстанавливаем старые колонки (тоже без данных)
    op.drop_column('dialogs', 'name')
    op.drop_column('dialogs', 'email')
    
    op.add_column('dialogs', sa.Column('guest_name', sa.String(length=100), nullable=True))
    op.add_column('dialogs', sa.Column('guest_email', sa.String(length=120), nullable=True))