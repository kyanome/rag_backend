# RAG Backend

Enterprise RAG (Retrieval-Augmented Generation) system backend.

## Setup

```bash
# Install dependencies
make setup

# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials

# Run development server
make dev
```

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
