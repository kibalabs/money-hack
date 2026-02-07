"""add cross_chain_actions table

Revision ID: a1b2c3d4e5f6
Revises: f305a3e51bae
Create Date: 2026-02-07 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f305a3e51bae'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tbl_cross_chain_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=False),
        sa.Column('updated_date', sa.DateTime(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(), nullable=False),
        sa.Column('action_type', sa.Text(), nullable=False),
        sa.Column('from_chain', sa.Integer(), nullable=False),
        sa.Column('to_chain', sa.Integer(), nullable=False),
        sa.Column('from_token', sa.Text(), nullable=False),
        sa.Column('to_token', sa.Text(), nullable=False),
        sa.Column('amount', sa.Text(), nullable=False),
        sa.Column('tx_hash', sa.Text(), nullable=True),
        sa.Column('bridge_name', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tbl_cross_chain_actions_agent_id', 'tbl_cross_chain_actions', ['agent_id'])


def downgrade():
    op.drop_index('ix_tbl_cross_chain_actions_agent_id', table_name='tbl_cross_chain_actions')
    op.drop_table('tbl_cross_chain_actions')
