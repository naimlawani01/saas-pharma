"""create license tables

Revision ID: create_license_tables
Revises: add_business_type
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_license_tables'
down_revision: Union[str, None] = 'add_business_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Vérifier si les tables existent déjà
    from sqlalchemy.engine import reflection
    
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()
    
    # Créer la table licenses si elle n'existe pas
    if 'licenses' not in existing_tables:
        op.create_table(
            'licenses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('license_key', sa.String(), nullable=False),
            sa.Column('pharmacy_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='active'),
            sa.Column('max_activations', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('customer_name', sa.String(), nullable=True),
            sa.Column('customer_email', sa.String(), nullable=True),
            sa.Column('customer_phone', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_licenses_id'), 'licenses', ['id'], unique=False)
        op.create_index(op.f('ix_licenses_license_key'), 'licenses', ['license_key'], unique=True)
    else:
        # Vérifier et créer les index s'ils n'existent pas
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('licenses')]
            if 'ix_licenses_id' not in existing_indexes:
                op.create_index(op.f('ix_licenses_id'), 'licenses', ['id'], unique=False)
            if 'ix_licenses_license_key' not in existing_indexes:
                op.create_index(op.f('ix_licenses_license_key'), 'licenses', ['license_key'], unique=True)
        except Exception:
            pass  # Si on ne peut pas vérifier les index, on continue
    
    # Créer la table license_activations si elle n'existe pas
    if 'license_activations' not in existing_tables:
        op.create_table(
            'license_activations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('license_id', sa.Integer(), nullable=False),
            sa.Column('hardware_id', sa.String(), nullable=False),
            sa.Column('machine_name', sa.String(), nullable=True),
            sa.Column('os_info', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('activation_token', sa.String(), nullable=False),
            sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('activation_token')
        )
        op.create_index(op.f('ix_license_activations_id'), 'license_activations', ['id'], unique=False)
        op.create_index(op.f('ix_license_activations_license_id'), 'license_activations', ['license_id'], unique=False)
        op.create_index(op.f('ix_license_activations_hardware_id'), 'license_activations', ['hardware_id'], unique=False)
        op.create_index(op.f('ix_license_activations_activation_token'), 'license_activations', ['activation_token'], unique=True)
    else:
        # Vérifier et créer les index s'ils n'existent pas
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('license_activations')]
            if 'ix_license_activations_id' not in existing_indexes:
                op.create_index(op.f('ix_license_activations_id'), 'license_activations', ['id'], unique=False)
            if 'ix_license_activations_license_id' not in existing_indexes:
                op.create_index(op.f('ix_license_activations_license_id'), 'license_activations', ['license_id'], unique=False)
            if 'ix_license_activations_hardware_id' not in existing_indexes:
                op.create_index(op.f('ix_license_activations_hardware_id'), 'license_activations', ['hardware_id'], unique=False)
            if 'ix_license_activations_activation_token' not in existing_indexes:
                op.create_index(op.f('ix_license_activations_activation_token'), 'license_activations', ['activation_token'], unique=True)
        except Exception:
            pass  # Si on ne peut pas vérifier les index, on continue


def downgrade() -> None:
    op.drop_index(op.f('ix_license_activations_activation_token'), table_name='license_activations')
    op.drop_index(op.f('ix_license_activations_hardware_id'), table_name='license_activations')
    op.drop_index(op.f('ix_license_activations_license_id'), table_name='license_activations')
    op.drop_index(op.f('ix_license_activations_id'), table_name='license_activations')
    op.drop_table('license_activations')
    op.drop_index(op.f('ix_licenses_license_key'), table_name='licenses')
    op.drop_index(op.f('ix_licenses_id'), table_name='licenses')
    op.drop_table('licenses')

