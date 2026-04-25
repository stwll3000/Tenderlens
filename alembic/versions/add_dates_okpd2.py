"""
Миграция: добавление полей дат и ОКПД2 в таблицу lots

Revision ID: add_dates_okpd2
Revises: 
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_dates_okpd2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новые колонки
    op.add_column('lots', sa.Column('published_date', sa.String(20), nullable=True))
    op.add_column('lots', sa.Column('updated_date', sa.String(20), nullable=True))
    op.add_column('lots', sa.Column('deadline_date', sa.String(20), nullable=True))
    op.add_column('lots', sa.Column('okpd2_codes', sa.Text(), nullable=True))
    op.add_column('lots', sa.Column('participants_count', sa.Integer(), nullable=True))
    
    # Создаём индексы для дат
    op.create_index('idx_published_date', 'lots', ['published_date'])
    op.create_index('idx_deadline_date', 'lots', ['deadline_date'])


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('idx_deadline_date', table_name='lots')
    op.drop_index('idx_published_date', table_name='lots')
    
    # Удаляем колонки
    op.drop_column('lots', 'participants_count')
    op.drop_column('lots', 'okpd2_codes')
    op.drop_column('lots', 'deadline_date')
    op.drop_column('lots', 'updated_date')
    op.drop_column('lots', 'published_date')
