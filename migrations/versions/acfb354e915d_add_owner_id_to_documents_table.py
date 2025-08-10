"""Add owner_id to documents table

Revision ID: acfb354e915d
Revises: 4f2030b1b448
Create Date: 2025-08-08 15:30:20.925129

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "acfb354e915d"
down_revision: str | Sequence[str] | None = "4f2030b1b448"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if using SQLite
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # Use batch mode for SQLite
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.add_column(sa.Column("owner_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                "fk_documents_owner_id_users", "users", ["owner_id"], ["id"]
            )
    else:
        # Standard ALTER TABLE for other databases (PostgreSQL, etc.)
        op.add_column("documents", sa.Column("owner_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_documents_owner_id_users", "documents", "users", ["owner_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Check if using SQLite
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # Use batch mode for SQLite
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.drop_constraint("fk_documents_owner_id_users", type_="foreignkey")
            batch_op.drop_column("owner_id")
    else:
        # Standard ALTER TABLE for other databases (PostgreSQL, etc.)
        op.drop_constraint(
            "fk_documents_owner_id_users", "documents", type_="foreignkey"
        )
        op.drop_column("documents", "owner_id")
