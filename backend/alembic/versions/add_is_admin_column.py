"""Add is_admin column to users table

Revision ID: add_is_admin_col
Revises: 
Create Date: 2025-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_is_admin_col'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_admin column to users table"""
    op.add_column('users', 
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Set admin@tidyframe.com as admin if it exists
    op.execute("""
        UPDATE users 
        SET is_admin = true 
        WHERE email = 'admin@tidyframe.com'
    """)


def downgrade() -> None:
    """Remove is_admin column from users table"""
    op.drop_column('users', 'is_admin')