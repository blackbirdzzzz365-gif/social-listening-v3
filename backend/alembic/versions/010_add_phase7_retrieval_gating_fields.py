"""add phase 7 retrieval gating fields

Revision ID: 010_add_phase7_retrieval_gating_fields
Revises: 009_add_context_clarification_state
Create Date: 2026-03-31 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "010_add_phase7_retrieval_gating_fields"
down_revision = "009_add_context_clarification_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.add_column(sa.Column("retrieval_profile_json", sa.Text(), nullable=True))

    with op.batch_alter_table("crawled_posts") as batch_op:
        batch_op.add_column(sa.Column("processing_stage", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("pre_ai_status", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("pre_ai_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("pre_ai_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("score_breakdown_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("quality_flags_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("query_family", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_type", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_batch_index", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("batch_decision", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("provider_used", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("crawled_posts") as batch_op:
        batch_op.drop_column("fallback_used")
        batch_op.drop_column("provider_used")
        batch_op.drop_column("batch_decision")
        batch_op.drop_column("source_batch_index")
        batch_op.drop_column("source_type")
        batch_op.drop_column("query_family")
        batch_op.drop_column("quality_flags_json")
        batch_op.drop_column("score_breakdown_json")
        batch_op.drop_column("pre_ai_reason")
        batch_op.drop_column("pre_ai_score")
        batch_op.drop_column("pre_ai_status")
        batch_op.drop_column("processing_stage")

    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.drop_column("retrieval_profile_json")
