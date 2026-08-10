"""training jobs

Revision ID: 0002_training_jobs
Revises: 0001_initial_schema
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_training_jobs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("voice_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("dataset_path", sa.Text(), nullable=False),
        sa.Column("manifest_path", sa.Text(), nullable=False),
        sa.Column("model_ref", sa.String(length=255), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("request_meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_jobs_created_at", "training_jobs", ["created_at"], unique=False)
    op.create_index("ix_training_jobs_status", "training_jobs", ["status"], unique=False)
    op.create_index("ix_training_jobs_tenant_id", "training_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_training_jobs_voice_id", "training_jobs", ["voice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_training_jobs_voice_id", table_name="training_jobs")
    op.drop_index("ix_training_jobs_tenant_id", table_name="training_jobs")
    op.drop_index("ix_training_jobs_status", table_name="training_jobs")
    op.drop_index("ix_training_jobs_created_at", table_name="training_jobs")
    op.drop_table("training_jobs")
