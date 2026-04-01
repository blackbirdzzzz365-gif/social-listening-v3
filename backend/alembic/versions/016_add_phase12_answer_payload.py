"""add phase 12 answer payload

Revision ID: 016_add_phase12_answer_payload
Revises: 015_add_phase11_planning_metadata
Create Date: 2026-04-02 01:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "016_add_phase12_answer_payload"
down_revision = "015_add_phase11_planning_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.add_column(sa.Column("answer_payload_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("plan_runs") as batch_op:
        batch_op.drop_column("answer_payload_json")
