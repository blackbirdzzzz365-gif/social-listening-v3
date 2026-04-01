"""add phase 10 cancelling status

Revision ID: 014_add_phase10_cancelling_status
Revises: 013_add_phase9_run_state_fields
Create Date: 2026-04-01 09:30:00.000000
"""

from alembic import op


revision = "014_add_phase10_cancelling_status"
down_revision = "013_add_phase9_run_state_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_constraint("ck_plan_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_plan_runs_status",
            "status IN ('QUEUED','RUNNING','PAUSED','CANCELLING','DONE','FAILED','CANCELLED')",
        )


def downgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_constraint("ck_plan_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_plan_runs_status",
            "status IN ('QUEUED','RUNNING','PAUSED','DONE','FAILED','CANCELLED')",
        )
