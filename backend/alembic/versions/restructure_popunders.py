"""restructure_popunder_campaigns

Revision ID: restructure_popunders
Revises: add_popunder_campaigns
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'restructure_popunders'
down_revision: Union[str, Sequence[str], None] = 'add_popunder_campaigns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restructure popunder_campaigns to be independent from projects."""
    
    # Disable foreign key checks for clean drop
    op.execute("SET FOREIGN_KEY_CHECKS=0")
    
    # Drop the old table and recreate with new structure
    op.drop_table('popunder_campaigns')
    
    # Create new popunder_campaigns table with user_id instead of project_id
    op.create_table(
        'popunder_campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', name='popunder_status', create_type=False), nullable=False, server_default='active'),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('slug', name='uq_popunder_slug'),
    )
    op.create_index('ix_popunder_campaigns_user_id', 'popunder_campaigns', ['user_id'])
    op.create_index('ix_popunder_campaigns_slug', 'popunder_campaigns', ['slug'])
    
    # Create popunder_whitelists table
    op.create_table(
        'popunder_whitelists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('domain_pattern', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['campaign_id'], ['popunder_campaigns.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_popunder_whitelists_campaign_id', 'popunder_whitelists', ['campaign_id'])
    
    # Re-enable foreign key checks
    op.execute("SET FOREIGN_KEY_CHECKS=1")


def downgrade() -> None:
    """Revert to project-based popunder campaigns."""
    op.drop_index('ix_popunder_whitelists_campaign_id', table_name='popunder_whitelists')
    op.drop_table('popunder_whitelists')
    
    op.drop_index('ix_popunder_campaigns_slug', table_name='popunder_campaigns')
    op.drop_index('ix_popunder_campaigns_user_id', table_name='popunder_campaigns')
    op.drop_table('popunder_campaigns')
    
    # Recreate old structure
    op.create_table(
        'popunder_campaigns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', name='popunder_status'), nullable=False, server_default='active'),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'slug', name='uq_project_popunder_slug'),
    )
    op.create_index('ix_popunder_campaigns_project_id', 'popunder_campaigns', ['project_id'])
