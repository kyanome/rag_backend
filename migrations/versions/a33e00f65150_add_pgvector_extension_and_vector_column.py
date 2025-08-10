"""add pgvector extension and vector column

Revision ID: a33e00f65150
Revises: acfb354e915d
Create Date: 2025-08-09 18:41:14.435957

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector

# Import pgvector conditionally
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

# revision identifiers, used by Alembic.
revision: str = 'a33e00f65150'
down_revision: str | Sequence[str] | None = 'acfb354e915d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get database connection
    connection = op.get_bind()

    # Check if we're using PostgreSQL
    if connection.dialect.name == 'postgresql':
        # Create pgvector extension
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')

        # Add vector column if pgvector is available
        if PGVECTOR_AVAILABLE:
            # Add embedding_vector column
            op.add_column(
                'document_chunks',
                sa.Column('embedding_vector', Vector(1536), nullable=True)
            )

            # Create index for vector similarity search using ivfflat
            op.execute('''
                CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector 
                ON document_chunks 
                USING ivfflat (embedding_vector vector_cosine_ops) 
                WITH (lists = 100)
            ''')

            # Migrate existing embeddings from JSON to vector column
            op.execute('''
                UPDATE document_chunks 
                SET embedding_vector = embedding::vector 
                WHERE embedding IS NOT NULL 
                AND embedding_vector IS NULL
            ''')
        else:
            print("pgvector Python package not installed. Skipping vector column creation.")
    else:
        print(f"Non-PostgreSQL database detected ({connection.dialect.name}). Skipping pgvector setup.")


def downgrade() -> None:
    """Downgrade schema."""
    # Get database connection
    connection = op.get_bind()

    # Only attempt to remove PostgreSQL-specific features if using PostgreSQL
    if connection.dialect.name == 'postgresql':
        # Drop the index first
        op.execute('DROP INDEX IF EXISTS ix_document_chunks_embedding_vector')

        # Check if column exists before trying to drop it
        inspector = Inspector.from_engine(connection)
        columns = [col['name'] for col in inspector.get_columns('document_chunks')]

        if 'embedding_vector' in columns:
            # Copy vector data back to JSON column before dropping
            op.execute('''
                UPDATE document_chunks 
                SET embedding = array_to_json(ARRAY(SELECT unnest(embedding_vector::real[])))::jsonb 
                WHERE embedding_vector IS NOT NULL
            ''')

            # Drop the vector column
            op.drop_column('document_chunks', 'embedding_vector')

        # Note: We don't drop the extension as other tables might be using it
