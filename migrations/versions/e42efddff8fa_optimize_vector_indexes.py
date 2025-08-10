"""optimize_vector_indexes

Revision ID: e42efddff8fa
Revises: a33e00f65150
Create Date: 2025-08-10 07:53:04.096459

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e42efddff8fa"
down_revision: str | Sequence[str] | None = "a33e00f65150"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema with optimized indexes for vector search."""
    # PostgreSQL specific optimizations
    connection = op.get_bind()

    # Check if we're using PostgreSQL
    if connection.dialect.name == "postgresql":
        # First, ensure columns are JSONB type (required for GIN indexes)
        op.execute(
            "ALTER TABLE document_chunks ALTER COLUMN chunk_metadata TYPE jsonb USING chunk_metadata::jsonb"
        )
        op.execute(
            "ALTER TABLE documents ALTER COLUMN document_metadata TYPE jsonb USING document_metadata::jsonb"
        )
        # IVFFlat index for vector similarity search
        # Lists parameter affects index build time vs query performance
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_ivfflat
            ON document_chunks
            USING ivfflat (embedding_vector vector_cosine_ops)
            WITH (lists = 100);
        """
        )

        # GIN index for full text search on content
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_content_gin
            ON document_chunks
            USING gin(to_tsvector('english', content));
        """
        )

        # GIN index for Japanese text search
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_content_gin_ja
            ON document_chunks
            USING gin(to_tsvector('simple', content));
        """
        )

        # JSONB GIN index for metadata search
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata_gin
            ON document_chunks
            USING gin(chunk_metadata);
        """
        )

        # B-tree index for document_id foreign key lookups
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
            ON document_chunks(document_id);
        """
        )

        # B-tree index for created_at timestamp queries
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_created_at
            ON document_chunks(created_at DESC);
        """
        )

        # Composite index for document metadata queries
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin
            ON documents
            USING gin(document_metadata);
        """
        )

        # Index for document title search
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_title_trgm
            ON documents
            USING gin(title gin_trgm_ops);
        """
        )

        # Update table statistics for query planner
        op.execute("ANALYZE document_chunks;")
        op.execute("ANALYZE documents;")

    # SQLite optimizations
    elif connection.dialect.name == "sqlite":
        # Create indexes for SQLite
        op.create_index(
            "idx_document_chunks_document_id",
            "document_chunks",
            ["document_id"],
            if_not_exists=True,
        )

        op.create_index(
            "idx_document_chunks_created_at",
            "document_chunks",
            ["created_at"],
            if_not_exists=True,
        )

        op.create_index(
            "idx_documents_title", "documents", ["title"], if_not_exists=True
        )

        op.create_index(
            "idx_documents_created_at", "documents", ["created_at"], if_not_exists=True
        )


def downgrade() -> None:
    """Downgrade schema by removing optimized indexes."""
    connection = op.get_bind()

    if connection.dialect.name == "postgresql":
        # Drop PostgreSQL specific indexes
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding_ivfflat;")
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_content_gin;")
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_content_gin_ja;")
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_metadata_gin;")
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_document_id;")
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_created_at;")
        op.execute("DROP INDEX IF EXISTS idx_documents_metadata_gin;")
        op.execute("DROP INDEX IF EXISTS idx_documents_title_trgm;")

    elif connection.dialect.name == "sqlite":
        # Drop SQLite indexes
        op.drop_index("idx_document_chunks_document_id", "document_chunks")
        op.drop_index("idx_document_chunks_created_at", "document_chunks")
        op.drop_index("idx_documents_title", "documents")
        op.drop_index("idx_documents_created_at", "documents")
