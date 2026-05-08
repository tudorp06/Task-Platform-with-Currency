"""add submission attachments table

Revision ID: 20260508_01
Revises:
Create Date: 2026-05-08 12:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260508_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "submission_attachments" in inspector.get_table_names():
        return
    op.create_table(
        "submission_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "submission_attachments" not in inspector.get_table_names():
        return
    op.drop_table("submission_attachments")
