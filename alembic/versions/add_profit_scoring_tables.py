"""add profit scoring tables

Revision ID: add_profit_scoring
Revises: add_dates_okpd2
Create Date: 2026-04-26 08:21:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_profit_scoring'
down_revision = 'add_dates_okpd2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новые поля в таблицу customers
    op.add_column('customers', sa.Column('in_rnp', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('customers', sa.Column('completed_contracts_12m', sa.Integer(), nullable=True))
    op.add_column('customers', sa.Column('avg_payment_delay_days', sa.Float(), nullable=True))
    
    # Добавляем новые поля в таблицу lots
    op.add_column('lots', sa.Column('niche_slug', sa.String(length=100), nullable=True))
    op.add_column('lots', sa.Column('tz_text', sa.Text(), nullable=True))
    op.create_index('idx_niche_region', 'lots', ['niche_slug', 'region_code'])
    op.create_index(op.f('ix_lots_niche_slug'), 'lots', ['niche_slug'])
    
    # Создаем таблицу suppliers
    op.create_table('suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inn', sa.String(length=12), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('kpp', sa.String(length=9), nullable=True),
        sa.Column('region_code', sa.String(length=2), nullable=True),
        sa.Column('is_smp', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('in_rnp', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rnp_until', sa.DateTime(), nullable=True),
        sa.Column('egrul_revenue', sa.Float(), nullable=True),
        sa.Column('egrul_employees', sa.Integer(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inn')
    )
    op.create_index(op.f('ix_suppliers_inn'), 'suppliers', ['inn'], unique=True)
    op.create_index(op.f('ix_suppliers_region_code'), 'suppliers', ['region_code'])
    
    # Создаем таблицу lot_participations
    op.create_table('lot_participations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lot_id', sa.BigInteger(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('bid_price', sa.Float(), nullable=True),
        sa.Column('is_winner', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('rejected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lot_id', 'supplier_id', name='uq_lot_supplier')
    )
    op.create_index(op.f('ix_lot_participations_lot_id'), 'lot_participations', ['lot_id'])
    op.create_index(op.f('ix_lot_participations_supplier_id'), 'lot_participations', ['supplier_id'])
    op.create_index('idx_winner_lot', 'lot_participations', ['is_winner', 'lot_id'])
    op.create_index(op.f('ix_lot_participations_is_winner'), 'lot_participations', ['is_winner'])
    
    # Создаем таблицу lot_categories
    op.create_table('lot_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('okpd2_prefix', sa.String(length=20), nullable=False),
        sa.Column('niche_slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('okpd2_prefix', 'niche_slug', name='uq_okpd2_niche')
    )
    op.create_index(op.f('ix_lot_categories_okpd2_prefix'), 'lot_categories', ['okpd2_prefix'])
    op.create_index(op.f('ix_lot_categories_niche_slug'), 'lot_categories', ['niche_slug'])
    
    # Создаем таблицу price_benchmarks
    op.create_table('price_benchmarks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('niche_slug', sa.String(length=100), nullable=False),
        sa.Column('region_code', sa.String(length=2), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('median_initial_price', sa.Float(), nullable=False),
        sa.Column('median_final_price', sa.Float(), nullable=True),
        sa.Column('median_alpha', sa.Float(), nullable=True),
        sa.Column('avg_unique_suppliers', sa.Float(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_benchmarks_niche_slug'), 'price_benchmarks', ['niche_slug'])
    op.create_index(op.f('ix_price_benchmarks_region_code'), 'price_benchmarks', ['region_code'])
    op.create_index('idx_niche_region_period', 'price_benchmarks', ['niche_slug', 'region_code', 'period_end'])
    
    # Создаем таблицу lot_scores
    op.create_table('lot_scores',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('lot_id', sa.BigInteger(), nullable=False),
        sa.Column('profit_score', sa.Float(), nullable=False),
        sa.Column('margin_signal', sa.Float(), nullable=False),
        sa.Column('competition_signal', sa.Float(), nullable=False),
        sa.Column('captive_signal', sa.Float(), nullable=False),
        sa.Column('timing_signal', sa.Float(), nullable=False),
        sa.Column('spec_purity_signal', sa.Float(), nullable=False),
        sa.Column('customer_health', sa.Float(), nullable=False),
        sa.Column('flags_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('computed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lot_id')
    )
    op.create_index(op.f('ix_lot_scores_lot_id'), 'lot_scores', ['lot_id'], unique=True)
    op.create_index(op.f('ix_lot_scores_profit_score'), 'lot_scores', ['profit_score'])


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_index(op.f('ix_lot_scores_profit_score'), table_name='lot_scores')
    op.drop_index(op.f('ix_lot_scores_lot_id'), table_name='lot_scores')
    op.drop_table('lot_scores')
    
    op.drop_index('idx_niche_region_period', table_name='price_benchmarks')
    op.drop_index(op.f('ix_price_benchmarks_region_code'), table_name='price_benchmarks')
    op.drop_index(op.f('ix_price_benchmarks_niche_slug'), table_name='price_benchmarks')
    op.drop_table('price_benchmarks')
    
    op.drop_index(op.f('ix_lot_categories_niche_slug'), table_name='lot_categories')
    op.drop_index(op.f('ix_lot_categories_okpd2_prefix'), table_name='lot_categories')
    op.drop_table('lot_categories')
    
    op.drop_index(op.f('ix_lot_participations_is_winner'), table_name='lot_participations')
    op.drop_index('idx_winner_lot', table_name='lot_participations')
    op.drop_index(op.f('ix_lot_participations_supplier_id'), table_name='lot_participations')
    op.drop_index(op.f('ix_lot_participations_lot_id'), table_name='lot_participations')
    op.drop_table('lot_participations')
    
    op.drop_index(op.f('ix_suppliers_region_code'), table_name='suppliers')
    op.drop_index(op.f('ix_suppliers_inn'), table_name='suppliers')
    op.drop_table('suppliers')
    
    op.drop_index(op.f('ix_lots_niche_slug'), table_name='lots')
    op.drop_index('idx_niche_region', table_name='lots')
    op.drop_column('lots', 'tz_text')
    op.drop_column('lots', 'niche_slug')
    
    op.drop_column('customers', 'avg_payment_delay_days')
    op.drop_column('customers', 'completed_contracts_12m')
    op.drop_column('customers', 'in_rnp')
