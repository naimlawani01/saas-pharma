"""add_credit_management_tables

Revision ID: 269c57525a1a
Revises: dd394e2c978c
Create Date: 2025-12-09 12:11:55.985930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '269c57525a1a'
down_revision: Union[str, None] = 'dd394e2c978c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Vérifier si les tables existent déjà
    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Créer les types ENUM si nécessaire (avec vérification d'existence)
    # Vérifier si les types existent déjà
    def enum_exists(enum_name):
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"
        ), {"name": enum_name})
        return result.scalar()
    
    # Créer les types ENUM seulement s'ils n'existent pas
    if not enum_exists('credittransactiontype'):
        op.execute("CREATE TYPE credittransactiontype AS ENUM ('charge', 'payment', 'adjustment', 'refund')")
    if not enum_exists('paymentbreakdownmethod'):
        op.execute("CREATE TYPE paymentbreakdownmethod AS ENUM ('cash', 'card', 'mobile_money', 'check', 'bank_transfer')")
    
    # Définir les types pour utilisation dans les tables
    credit_transaction_type = sa.Enum('charge', 'payment', 'adjustment', 'refund', name='credittransactiontype', create_type=False)
    payment_breakdown_method = sa.Enum('cash', 'card', 'mobile_money', 'check', 'bank_transfer', name='paymentbreakdownmethod', create_type=False)
    
    # Créer customer_credit_accounts si n'existe pas
    if 'customer_credit_accounts' not in existing_tables:
        op.create_table(
            'customer_credit_accounts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pharmacy_id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('current_balance', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('credit_limit', sa.Float(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sync_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_customer_credit_accounts_pharmacy_id'), 'customer_credit_accounts', ['pharmacy_id'], unique=False)
        op.create_index(op.f('ix_customer_credit_accounts_customer_id'), 'customer_credit_accounts', ['customer_id'], unique=False)
        op.create_unique_constraint('uq_customer_credit_accounts_sync_id', 'customer_credit_accounts', ['sync_id'])
    else:
        # Table existe, modifier
        if 'current_balance' not in [col['name'] for col in inspector.get_columns('customer_credit_accounts')]:
            op.add_column('customer_credit_accounts', sa.Column('current_balance', sa.Float(), nullable=False, server_default='0.0'))
        if 'last_sync_at' not in [col['name'] for col in inspector.get_columns('customer_credit_accounts')]:
            op.add_column('customer_credit_accounts', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
        if 'sync_id' not in [col['name'] for col in inspector.get_columns('customer_credit_accounts')]:
            op.add_column('customer_credit_accounts', sa.Column('sync_id', sa.String(), nullable=True))
        
        # Vérifier et modifier les index/contraintes
        try:
            op.drop_index(op.f('ix_customer_credit_accounts_customer_id'), table_name='customer_credit_accounts')
        except:
            pass
        op.create_index(op.f('ix_customer_credit_accounts_customer_id'), 'customer_credit_accounts', ['customer_id'], unique=False)
        try:
            op.create_unique_constraint('uq_customer_credit_accounts_sync_id', 'customer_credit_accounts', ['sync_id'])
        except:
            pass
        
        # Supprimer balance si existe
        if 'balance' in [col['name'] for col in inspector.get_columns('customer_credit_accounts')]:
            op.drop_column('customer_credit_accounts', 'balance')
    
    # Créer credit_transactions si n'existe pas
    if 'credit_transactions' not in existing_tables:
        # Le type ENUM a déjà été créé plus haut si nécessaire
        op.create_table(
            'credit_transactions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pharmacy_id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('sale_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('transaction_type', credit_transaction_type, nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('balance_after', sa.Float(), nullable=False),
            sa.Column('reference_number', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sync_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
            sa.ForeignKeyConstraint(['account_id'], ['customer_credit_accounts.id'], ),
            sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_credit_transactions_pharmacy_id'), 'credit_transactions', ['pharmacy_id'], unique=False)
        op.create_index(op.f('ix_credit_transactions_account_id'), 'credit_transactions', ['account_id'], unique=False)
        op.create_index(op.f('ix_credit_transactions_sale_id'), 'credit_transactions', ['sale_id'], unique=False)
        op.create_index(op.f('ix_credit_transactions_transaction_type'), 'credit_transactions', ['transaction_type'], unique=False)
        op.create_index(op.f('ix_credit_transactions_reference_number'), 'credit_transactions', ['reference_number'], unique=False)
        op.create_unique_constraint('uq_credit_transactions_sync_id', 'credit_transactions', ['sync_id'])
    else:
        # Table existe, modifier
        # Le type ENUM a déjà été créé plus haut si nécessaire
        columns = [col['name'] for col in inspector.get_columns('credit_transactions')]
        
        if 'account_id' not in columns:
            op.add_column('credit_transactions', sa.Column('account_id', sa.Integer(), nullable=True))
            # Remplir account_id depuis credit_account_id si existe
            if 'credit_account_id' in columns:
                op.execute('UPDATE credit_transactions SET account_id = credit_account_id WHERE account_id IS NULL')
            op.alter_column('credit_transactions', 'account_id', nullable=False)
        
        if 'reference_number' not in columns:
            op.add_column('credit_transactions', sa.Column('reference_number', sa.String(), nullable=True))
        if 'last_sync_at' not in columns:
            op.add_column('credit_transactions', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
        if 'sync_id' not in columns:
            op.add_column('credit_transactions', sa.Column('sync_id', sa.String(), nullable=True))
        
        # Modifier les index/contraintes
        try:
            op.drop_index(op.f('ix_credit_transactions_credit_account_id'), table_name='credit_transactions')
        except:
            pass
        try:
            op.create_index(op.f('ix_credit_transactions_account_id'), 'credit_transactions', ['account_id'], unique=False)
        except:
            pass
        try:
            op.create_index(op.f('ix_credit_transactions_reference_number'), 'credit_transactions', ['reference_number'], unique=False)
        except:
            pass
        try:
            op.create_index(op.f('ix_credit_transactions_transaction_type'), 'credit_transactions', ['transaction_type'], unique=False)
        except:
            pass
        try:
            op.create_unique_constraint('uq_credit_transactions_sync_id', 'credit_transactions', ['sync_id'])
        except:
            pass
        
        # Modifier les foreign keys
        try:
            op.drop_constraint(op.f('credit_transactions_credit_account_id_fkey'), 'credit_transactions', type_='foreignkey')
        except:
            pass
        try:
            op.create_foreign_key('fk_credit_transactions_account_id', 'credit_transactions', 'customer_credit_accounts', ['account_id'], ['id'])
        except:
            pass
        
        # Supprimer les anciennes colonnes
        if 'reference' in columns:
            op.drop_column('credit_transactions', 'reference')
        if 'credit_account_id' in columns:
            op.drop_column('credit_transactions', 'credit_account_id')
    
    # Créer payment_breakdowns si n'existe pas
    if 'payment_breakdowns' not in existing_tables:
        # Le type ENUM a déjà été créé plus haut si nécessaire
        op.create_table(
            'payment_breakdowns',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('sale_id', sa.Integer(), nullable=False),
            sa.Column('credit_transaction_id', sa.Integer(), nullable=True),
            sa.Column('payment_method', payment_breakdown_method, nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('reference', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sync_id', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
            sa.ForeignKeyConstraint(['credit_transaction_id'], ['credit_transactions.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_payment_breakdowns_sale_id'), 'payment_breakdowns', ['sale_id'], unique=False)
        op.create_index(op.f('ix_payment_breakdowns_credit_transaction_id'), 'payment_breakdowns', ['credit_transaction_id'], unique=False)
        op.create_unique_constraint('uq_payment_breakdowns_sync_id', 'payment_breakdowns', ['sync_id'])
    else:
        # Table existe, modifier
        # Le type ENUM a déjà été créé plus haut si nécessaire
        columns = [col['name'] for col in inspector.get_columns('payment_breakdowns')]
        
        if 'last_sync_at' not in columns:
            op.add_column('payment_breakdowns', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
        if 'sync_id' not in columns:
            op.add_column('payment_breakdowns', sa.Column('sync_id', sa.String(), nullable=True))
        
        try:
            op.create_unique_constraint('uq_payment_breakdowns_sync_id', 'payment_breakdowns', ['sync_id'])
        except:
            pass


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'payment_breakdowns', type_='unique')
    op.drop_column('payment_breakdowns', 'sync_id')
    op.drop_column('payment_breakdowns', 'last_sync_at')
    op.add_column('customer_credit_accounts', sa.Column('balance', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'customer_credit_accounts', type_='unique')
    op.drop_index(op.f('ix_customer_credit_accounts_customer_id'), table_name='customer_credit_accounts')
    op.create_index(op.f('ix_customer_credit_accounts_customer_id'), 'customer_credit_accounts', ['customer_id'], unique=True)
    op.drop_column('customer_credit_accounts', 'sync_id')
    op.drop_column('customer_credit_accounts', 'last_sync_at')
    op.drop_column('customer_credit_accounts', 'current_balance')
    op.add_column('credit_transactions', sa.Column('credit_account_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('credit_transactions', sa.Column('reference', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'credit_transactions', type_='foreignkey')
    op.create_foreign_key(op.f('credit_transactions_credit_account_id_fkey'), 'credit_transactions', 'customer_credit_accounts', ['credit_account_id'], ['id'])
    op.drop_constraint(None, 'credit_transactions', type_='unique')
    op.drop_index(op.f('ix_credit_transactions_transaction_type'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_reference_number'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_account_id'), table_name='credit_transactions')
    op.create_index(op.f('ix_credit_transactions_credit_account_id'), 'credit_transactions', ['credit_account_id'], unique=False)
    op.drop_column('credit_transactions', 'sync_id')
    op.drop_column('credit_transactions', 'last_sync_at')
    op.drop_column('credit_transactions', 'reference_number')
    op.drop_column('credit_transactions', 'account_id')
    # ### end Alembic commands ###
