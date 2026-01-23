.PHONY: install dev test lint format typecheck ty docs docs-build build clean help

install:
	uv sync

dev:
	uv sync --group dev

test:
	uv run pytest

test-cov:
	uv run pytest --cov=pacta --cov-report=term-missing

lint:
	uv run ruff check pacta tests

format:
	uv run ruff format pacta tests
	uv run ruff check --fix pacta tests

typecheck:
	uv run ty check pacta

docs:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build

build:
	uv build

clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache site
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:
	@echo "Available targets:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Install with dev dependencies"
	@echo "  test       - Run tests"
	@echo "  test-cov   - Run tests with coverage"
	@echo "  lint       - Run ruff linter"
	@echo "  format     - Format code with ruff"
	@echo "  typecheck  - Run ty type checker"
	@echo "  docs       - Serve documentation locally"
	@echo "  docs-build - Build documentation"
	@echo "  build      - Build package"
	@echo "  clean      - Remove build artifacts"
