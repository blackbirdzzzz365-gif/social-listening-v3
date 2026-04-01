"""add phase 11 planning metadata

Revision ID: 015_add_phase11_planning_metadata
Revises: 014_add_phase10_cancelling_status
Create Date: 2026-04-01 10:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "015_add_phase11_planning_metadata"
down_revision = "014_add_phase10_cancelling_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.add_column(sa.Column("planning_meta_json", sa.Text(), nullable=True))

    with op.batch_alter_table("plans") as batch_op:
        batch_op.add_column(sa.Column("generation_meta_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("plans") as batch_op:
        batch_op.drop_column("generation_meta_json")

    with op.batch_alter_table("product_contexts") as batch_op:
        batch_op.drop_column("planning_meta_json")
