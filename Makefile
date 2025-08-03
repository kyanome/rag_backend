.PHONY: help setup install check test format lint type-check clean run dev

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup       - Set up development environment"
	@echo "  make install     - Install dependencies"
	@echo "  make check       - Run all quality checks (lint, type-check, test)"
	@echo "  make test        - Run tests"
	@echo "  make format      - Format code"
	@echo "  make lint        - Run linting"
	@echo "  make type-check  - Run type checking"
	@echo "  make clean       - Clean temporary files"
	@echo "  make run         - Run the application"
	@echo "  make dev         - Run in development mode with auto-reload"

# Set up development environment
setup:
	@echo "Setting up development environment..."
	uv venv
	uv sync --dev
	@echo "Development environment ready!"

# Install dependencies
install:
	uv sync

# Run all quality checks
check: lint type-check test

# Run tests
test:
	uv run pytest

# Format code
format:
	uv run black src tests
	uv run ruff check --fix src tests

# Run linting
lint:
	uv run ruff check src tests
	uv run black --check src tests

# Run type checking
type-check:
	uv run mypy src

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Run the application
run:
	uv run uvicorn src.presentation.main:app --host 0.0.0.0 --port 8000

# Run in development mode
dev:
	uv run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000