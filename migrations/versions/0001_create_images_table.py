"""create images table

Revision ID: 0001
Revises:
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "done", "failed", name="image_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("original_file_name", sa.String(), nullable=False),
        sa.Column("original_storage_path", sa.String(), nullable=False),
        sa.Column("thumbnail_storage_path", sa.String(), nullable=True),
        sa.Column("preset", sa.String(), nullable=True),
        sa.Column("custom_width", sa.Integer(), nullable=True),
        sa.Column("custom_height", sa.Integer(), nullable=True),
        sa.Column("original_width", sa.Integer(), nullable=False),
        sa.Column("original_height", sa.Integer(), nullable=False),
        sa.Column("thumbnail_width", sa.Integer(), nullable=True),
        sa.Column("thumbnail_height", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_images_status_created_at", "images", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_images_status_created_at", table_name="images")
    op.drop_table("images")
    sa.Enum(name="image_status").drop(op.get_bind(), checkfirst=True)
