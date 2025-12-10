"""create_credit_management_tables_from_scratch

Revision ID: a9912b1b55af
Revises: 269c57525a1a
Create Date: 2025-12-10 18:13:40.029359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9912b1b55af'
down_revision: Union[str, None] = '269c57525a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
