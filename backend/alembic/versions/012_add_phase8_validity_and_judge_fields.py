"""add phase 8 validity and judge fields

Revision ID: 012_add_phase8_validity_and_judge_fields
Revises: 011_add_plan_run_completion_reason
Create Date: 2026-03-31 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "012_add_phase8_validity_and_judge_fields"
down_revision = "011_add_plan_run_completion_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.add_column(sa.Column("validity_spec_json", sa.Text(), nullable=True))

    with op.batch_alter_table("crawled_posts") as batch_op:
        batch_op.add_column(sa.Column("judge_decision", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_relevance_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("judge_confidence_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("judge_reason_codes_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_rationale", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_used_image_understanding", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("judge_image_summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_model_family", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_model_version", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_policy_version", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("judge_cache_key", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("crawled_posts") as batch_op:
        batch_op.drop_column("judge_cache_key")
        batch_op.drop_column("judge_policy_version")
        batch_op.drop_column("judge_model_version")
        batch_op.drop_column("judge_model_family")
        batch_op.drop_column("judge_image_summary")
        batch_op.drop_column("judge_used_image_understanding")
        batch_op.drop_column("judge_rationale")
        batch_op.drop_column("judge_reason_codes_json")
        batch_op.drop_column("judge_confidence_score")
        batch_op.drop_column("judge_relevance_score")
        batch_op.drop_column("judge_decision")

    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.drop_column("validity_spec_json")
