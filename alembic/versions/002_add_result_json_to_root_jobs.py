"""Add result_json to root_jobs

Revision ID: 002
Revises: 001
Create Date: 2024-11-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add result_json column to root_jobs table
    op.add_column('root_jobs', sa.Column('result_json', postgresql.JSONB(), nullable=True))
    
    # Create GIN index on result_json for JSON queries
    op.execute('CREATE INDEX idx_root_jobs_result_json ON root_jobs USING GIN (result_json)')


def downgrade() -> None:
    # Drop the index first
    op.execute('DROP INDEX IF EXISTS idx_root_jobs_result_json')
    
    # Drop the column
    op.drop_column('root_jobs', 'result_json')

