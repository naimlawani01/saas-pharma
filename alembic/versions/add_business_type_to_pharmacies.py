"""add business_type to pharmacies

Revision ID: add_business_type
Revises: f06f59528506
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_business_type'
down_revision: Union[str, None] = 'f06f59528506'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajouter la colonne business_type avec une valeur par défaut de 'general'
    # Cela permet aux commerces existants de continuer à fonctionner
    with op.batch_alter_table('pharmacies', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('business_type', sa.String(), nullable=False, server_default='general')
        )


def downgrade() -> None:
    with op.batch_alter_table('pharmacies', schema=None) as batch_op:
        batch_op.drop_column('business_type')

