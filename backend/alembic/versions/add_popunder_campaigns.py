"""add_popunder_campaigns

Revision ID: add_popunder_campaigns
Revises: f40711bb3a30
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_popunder_campaigns'
down_revision: Union[str, Sequence[str], None] = 'f40711bb3a30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create popunder_campaigns table."""
    op.create_table(
        'popunder_campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', name='popunder_status'), nullable=False, server_default='active'),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'slug', name='uq_project_popunder_slug'),
    )
    op.create_index('ix_popunder_campaigns_project_id', 'popunder_campaigns', ['project_id'])


def downgrade() -> None:
    """Drop popunder_campaigns table."""
    op.drop_index('ix_popunder_campaigns_project_id', table_name='popunder_campaigns')
    op.drop_table('popunder_campaigns')
    op.execute("DROP TYPE IF EXISTS popunder_status")
