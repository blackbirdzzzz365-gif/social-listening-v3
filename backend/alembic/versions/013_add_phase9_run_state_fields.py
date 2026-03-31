"""add phase 9 run state fields

Revision ID: 013_add_phase9_run_state_fields
Revises: 012_add_phase8_validity_and_judge_fields
Create Date: 2026-03-31 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "013_add_phase9_run_state_fields"
down_revision = "012_add_phase8_validity_and_judge_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.add_column(sa.Column("failure_class", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("answer_status", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("answer_generated_at", sa.Text(), nullable=True))

    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_constraint("ck_plan_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_plan_runs_status",
            "status IN ('QUEUED','RUNNING','PAUSED','DONE','FAILED','CANCELLED')",
        )


def downgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_constraint("ck_plan_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_plan_runs_status",
            "status IN ('RUNNING','PAUSED','DONE','FAILED','CANCELLED')",
        )

    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_column("answer_generated_at")
        batch_op.drop_column("answer_status")
        batch_op.drop_column("failure_class")
