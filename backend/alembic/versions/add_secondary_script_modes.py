"""Add secondary script mode and links columns

Revision ID: add_secondary_script_modes
Revises: restructure_popunders
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_secondary_script_modes'
down_revision = 'restructure_popunders'
branch_labels = None
depends_on = None


def upgrade():
    # Add secondary_script_mode column with default 'js'
    op.add_column('projects', sa.Column('secondary_script_mode', sa.String(20), nullable=False, server_default='js'))
    
    # Add secondary_script_links as JSON column
    op.add_column('projects', sa.Column('secondary_script_links', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('projects', 'secondary_script_links')
    op.drop_column('projects', 'secondary_script_mode')
