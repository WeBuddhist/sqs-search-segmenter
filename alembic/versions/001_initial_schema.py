"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create root_jobs table
    op.create_table(
        'root_jobs',
        sa.Column('job_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('manifestation_id', sa.Text(), nullable=False),
        sa.Column('total_segments', sa.Integer(), nullable=False),
        sa.Column('completed_segments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='QUEUED'
        ),
        sa.Column('merged_result_location', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('QUEUED','IN_PROGRESS','COMPLETED','FAILED')",
            name='root_job_status_check'
        )
    )
    
    # Create indexes for root_jobs
    op.create_index('idx_root_jobs_manifestation_id', 'root_jobs', ['manifestation_id'])
    op.create_index('idx_root_jobs_status', 'root_jobs', ['status'])
    op.create_index('idx_root_jobs_created_at', 'root_jobs', ['created_at'])
    
    # Create manifestation_tasks table
    op.create_table(
        'manifestation_tasks',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manifestation_id', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='QUEUED'
        ),
        sa.Column('result_json', postgresql.JSONB(), nullable=True),
        sa.Column('result_location', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['job_id'], ['root_jobs.job_id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "status IN ('QUEUED','IN_PROGRESS','COMPLETED','FAILED','RETRYING')",
            name='manifestation_task_status_check'
        )
    )
    
    # Create indexes for manifestation_tasks
    op.create_index('idx_manifestation_tasks_job_id', 'manifestation_tasks', ['job_id'])
    op.create_index('idx_manifestation_tasks_manifestation_id', 'manifestation_tasks', ['manifestation_id'])
    op.create_index('idx_manifestation_tasks_status', 'manifestation_tasks', ['status'])
    op.create_index('idx_manifestation_tasks_job_manifestation', 'manifestation_tasks', ['job_id', 'manifestation_id'])
    
    # Create GIN index on result_json for JSON queries
    op.execute('CREATE INDEX idx_manifestation_tasks_result_json ON manifestation_tasks USING GIN (result_json)')
    
    # Create trigger function for updated_at
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    # Create triggers
    op.execute('''
        CREATE TRIGGER update_root_jobs_updated_at
        BEFORE UPDATE ON root_jobs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    op.execute('''
        CREATE TRIGGER update_manifestation_tasks_updated_at
        BEFORE UPDATE ON manifestation_tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    # Create views for monitoring
    op.execute('''
        CREATE OR REPLACE VIEW job_progress_summary AS
        SELECT 
            rj.job_id,
            rj.manifestation_id,
            rj.status AS job_status,
            rj.total_segments,
            rj.completed_segments,
            ROUND((rj.completed_segments::NUMERIC / NULLIF(rj.total_segments, 0)) * 100, 2) AS progress_percentage,
            COUNT(mt.task_id) AS total_tasks,
            COUNT(CASE WHEN mt.status = 'COMPLETED' THEN 1 END) AS completed_tasks,
            COUNT(CASE WHEN mt.status = 'FAILED' THEN 1 END) AS failed_tasks,
            COUNT(CASE WHEN mt.status = 'RETRYING' THEN 1 END) AS retrying_tasks,
            rj.created_at,
            rj.updated_at
        FROM root_jobs rj
        LEFT JOIN manifestation_tasks mt ON rj.job_id = mt.job_id
        GROUP BY rj.job_id, rj.manifestation_id, rj.status, rj.total_segments, 
                 rj.completed_segments, rj.created_at, rj.updated_at;
    ''')
    
    op.execute('''
        CREATE OR REPLACE VIEW failed_jobs_summary AS
        SELECT 
            mt.job_id,
            mt.manifestation_id,
            mt.status,
            mt.error_message,
            mt.updated_at AS last_error_at,
            COUNT(*) OVER (PARTITION BY mt.job_id) AS total_errors_for_job
        FROM manifestation_tasks mt
        WHERE mt.status IN ('FAILED', 'RETRYING')
        ORDER BY mt.updated_at DESC;
    ''')


def downgrade() -> None:
    # Drop views
    op.execute('DROP VIEW IF EXISTS failed_jobs_summary')
    op.execute('DROP VIEW IF EXISTS job_progress_summary')
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_manifestation_tasks_updated_at ON manifestation_tasks')
    op.execute('DROP TRIGGER IF EXISTS update_root_jobs_updated_at ON root_jobs')
    
    # Drop trigger function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop tables (CASCADE will handle foreign keys)
    op.drop_table('manifestation_tasks')
    op.drop_table('root_jobs')

