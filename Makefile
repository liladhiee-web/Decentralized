# ==============================================================================
# Decentralized AI Compute Cloud Platform - Management Makefile
# ==============================================================================

.PHONY: help install dev test lint format migrate deploy clean

help:
	@echo "Decentralized AI Cloud Platform CLI Commands:"
	@echo "  make install   - Install production and development dependencies"
	@echo "  make dev       - Run coordinator in local hot-reload development mode"
	@echo "  make test      - Execute unit and integration tests with pytest"
	@echo "  make lint      - Check code style and formatting using Ruff"
	@echo "  make format    - Auto-format codebase using Ruff"
	@echo "  make migrate   - Execute Alembic database migrations"
	@echo "  make deploy    - Build and launch production Docker Compose stack"
	@echo "  make clean     - Remove cache files, test artifacts, and build outputs"

install:
	pip install --upgrade pip setuptools wheel
	pip install -e ".[dev,worker]"

dev:
	uvicorn coordinator.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ -v --tb=short

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

migrate:
	alembic upgrade head

deploy:
	docker compose up -d --build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[cod]" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov build dist *.egg-info test_cloudai.db

