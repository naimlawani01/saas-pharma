"""add_prescriptions_table

Revision ID: ecd9c828ca1f
Revises: 1ef3916e8491
Create Date: 2025-12-06 19:00:09.456241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ecd9c828ca1f'
down_revision: Union[str, None] = '1ef3916e8491'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Créer le type ENUM s'il n'existe pas déjà (idempotent)
    prescription_status_enum = postgresql.ENUM(
        'active',
        'used',
        'partially_used',
        'expired',
        'cancelled',
        name='prescriptionstatus',
        create_type=False,  # ne pas auto-créer lors du create_table
    )
    prescription_status_enum.create(conn, checkfirst=True)
    
    # Vérifier si la table prescriptions existe déjà
    result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prescriptions')"))
    table_exists = result.scalar()
    
    if table_exists:
        # Si la table existe, vérifier si la colonne prescription_id existe dans sales
        result = conn.execute(sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'sales' AND column_name = 'prescription_id'
            )
        """))
        column_exists = result.scalar()
        if not column_exists:
            op.add_column('sales', sa.Column('prescription_id', sa.Integer(), nullable=True))
            op.create_foreign_key(None, 'sales', 'prescriptions', ['prescription_id'], ['id'])
        return
    
    # Créer la table prescriptions
    op.create_table(
        'prescriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pharmacy_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('prescription_number', sa.String(), nullable=False),
        sa.Column('doctor_name', sa.String(), nullable=False),
        sa.Column('doctor_specialty', sa.String(), nullable=True),
        sa.Column('doctor_license_number', sa.String(), nullable=True),
        sa.Column('doctor_phone', sa.String(), nullable=True),
        sa.Column('prescription_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', prescription_status_enum, nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['pharmacy_id'], ['pharmacies.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescriptions_id'), 'prescriptions', ['id'], unique=False)
    op.create_index(op.f('ix_prescriptions_pharmacy_id'), 'prescriptions', ['pharmacy_id'], unique=False)
    op.create_index(op.f('ix_prescriptions_customer_id'), 'prescriptions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_prescriptions_prescription_number'), 'prescriptions', ['prescription_number'], unique=False)
    
    # Créer la table prescription_items
    op.create_table(
        'prescription_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prescription_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity_prescribed', sa.Integer(), nullable=False),
        sa.Column('quantity_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dosage', sa.String(), nullable=True),
        sa.Column('duration', sa.String(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescription_items_id'), 'prescription_items', ['id'], unique=False)
    op.create_index(op.f('ix_prescription_items_prescription_id'), 'prescription_items', ['prescription_id'], unique=False)
    
    # Ajouter la colonne prescription_id à la table sales
    op.add_column('sales', sa.Column('prescription_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'sales', 'prescriptions', ['prescription_id'], ['id'])


def downgrade() -> None:
    # Supprimer la colonne prescription_id de sales
    op.drop_constraint(None, 'sales', type_='foreignkey')
    op.drop_column('sales', 'prescription_id')
    
    # Supprimer la table prescription_items
    op.drop_index(op.f('ix_prescription_items_prescription_id'), table_name='prescription_items')
    op.drop_index(op.f('ix_prescription_items_id'), table_name='prescription_items')
    op.drop_table('prescription_items')
    
    # Supprimer la table prescriptions
    op.drop_index(op.f('ix_prescriptions_prescription_number'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_customer_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_pharmacy_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_id'), table_name='prescriptions')
    op.drop_table('prescriptions')
    
    # Supprimer l'enum (si plus utilisée)
    prescription_status_enum = postgresql.ENUM(
        'active',
        'used',
        'partially_used',
        'expired',
        'cancelled',
        name='prescriptionstatus',
        create_type=False,
    )
    prescription_status_enum.drop(op.get_bind(), checkfirst=True)
