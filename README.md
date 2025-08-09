# RAG Backend

Enterprise RAG (Retrieval-Augmented Generation) system backend.

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL with pgvector extension (for production)
- Docker (optional, for local PostgreSQL with pgvector)

### Installation

```bash
# Install dependencies
make setup

# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials

# Start PostgreSQL with pgvector (optional, for local development)
docker-compose up -d

# Run database migrations
uv run alembic upgrade head

# Run development server
make dev
```

### Database Configuration

This project supports both SQLite (for testing) and PostgreSQL with pgvector (for production):

- **SQLite**: Default for testing, no setup required
- **PostgreSQL with pgvector**: Required for vector similarity search

To use PostgreSQL with pgvector:
1. Start the database using `docker-compose up -d`
2. Update `DATABASE_URL` in `.env` to: `postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragdb`
3. Run migrations: `uv run alembic upgrade head`

## Development

```bash
make check    # Run all quality checks
make test     # Run tests
make format   # Format code
make lint     # Run linting
```

## Architecture

- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases
- **Infrastructure Layer**: External services, database
- **Presentation Layer**: REST API

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
