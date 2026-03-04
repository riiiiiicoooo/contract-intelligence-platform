.PHONY: help install install-dev test lint format clean docker-build docker-up docker-down db-init db-seed db-migrate api demo docs

# Default target
help:
	@echo "Contract Intelligence Platform - Makefile"
	@echo ""
	@echo "Installation & Setup:"
	@echo "  make install              - Install Python dependencies"
	@echo "  make install-dev          - Install with development dependencies"
	@echo "  make venv                 - Create Python virtual environment"
	@echo ""
	@echo "Database:"
	@echo "  make db-init              - Initialize PostgreSQL database (create schema)"
	@echo "  make db-seed              - Load sample M&A deal data"
	@echo "  make db-migrate           - Run database migrations"
	@echo "  make db-reset             - DROP and recreate database (destructive!)"
	@echo ""
	@echo "Development:"
	@echo "  make api                  - Run FastAPI development server (localhost:8000)"
	@echo "  make demo                 - Run demo pipeline script"
	@echo "  make test                 - Run pytest suite"
	@echo "  make test-cov             - Run tests with coverage report"
	@echo "  make lint                 - Run linting checks (flake8, mypy, pylint)"
	@echo "  make format               - Auto-format code (black, isort)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build         - Build Docker image"
	@echo "  make docker-up            - Start Docker containers (API + PostgreSQL + Redis)"
	@echo "  make docker-down          - Stop Docker containers"
	@echo "  make docker-logs          - Tail Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean                - Remove __pycache__, .pytest_cache, .mypy_cache"
	@echo "  make clean-all            - Clean + remove virtual environment"
	@echo ""

# ============================================================================
# INSTALLATION & ENVIRONMENT
# ============================================================================

venv:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip setuptools wheel

install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements.txt --only-binary :all:

# ============================================================================
# DATABASE
# ============================================================================

db-init:
	@echo "Initializing database schema..."
	psql -h localhost -U postgres -d contract_intelligence -f schema/schema.sql
	@echo "✓ Schema initialized"

db-seed:
	@echo "Seeding sample deal data..."
	psql -h localhost -U postgres -d contract_intelligence -f schema/seed.sql
	@echo "✓ Sample data loaded"

db-migrate:
	@echo "Running Alembic migrations..."
	alembic upgrade head

db-reset:
	@echo "WARNING: This will DROP the contract_intelligence database"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		dropdb -h localhost -U postgres contract_intelligence 2>/dev/null; \
		createdb -h localhost -U postgres contract_intelligence; \
		make db-init; \
		make db-seed; \
		echo "✓ Database reset complete"; \
	else \
		echo "Cancelled"; \
	fi

db-psql:
	psql -h localhost -U postgres -d contract_intelligence

# ============================================================================
# DEVELOPMENT
# ============================================================================

api:
	@echo "Starting FastAPI development server..."
	@echo "API will be available at: http://localhost:8000"
	@echo "API documentation: http://localhost:8000/docs"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

demo:
	@echo "Running contract analysis demo pipeline..."
	python demo/run_pipeline.py

test:
	@echo "Running pytest suite..."
	pytest tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report: htmlcov/index.html"

lint:
	@echo "Running linting checks..."
	flake8 src tests --max-line-length=100 --exclude=__pycache__
	mypy src --strict
	pylint src
	@echo "✓ Linting complete"

format:
	@echo "Auto-formatting code..."
	black src tests demo
	isort src tests demo
	@echo "✓ Formatting complete"

# ============================================================================
# DOCKER
# ============================================================================

docker-build:
	@echo "Building Docker image..."
	docker build -t contract-intelligence-platform:latest .
	@echo "✓ Image built"

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d
	@echo "✓ Containers started"
	@echo ""
	@echo "Services:"
	@echo "  FastAPI:    http://localhost:8000"
	@echo "  Postgres:   localhost:5432"
	@echo "  Redis:      localhost:6379"

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down
	@echo "✓ Containers stopped"

docker-logs:
	docker-compose logs -f

docker-logs-api:
	docker-compose logs -f api

docker-logs-db:
	docker-compose logs -f postgres

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
	@echo "✓ Cleanup complete"

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf venv
	@echo "✓ Full cleanup complete"

# ============================================================================
# UTILITY TARGETS
# ============================================================================

# List all contracts in database
db-list-contracts:
	psql -h localhost -U postgres -d contract_intelligence \
		-c "SELECT id, filename, contract_type, processing_status, created_at FROM contracts ORDER BY created_at DESC;"

# Show deal summary
db-deal-summary:
	psql -h localhost -U postgres -d contract_intelligence \
		-c "SELECT * FROM deal_summary;"

# Count clauses by risk level
db-risk-summary:
	psql -h localhost -U postgres -d contract_intelligence \
		-c "SELECT risk_level, COUNT(*) as count FROM clauses GROUP BY risk_level ORDER BY CASE risk_level WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END;"

# Show pending human reviews
db-pending-reviews:
	psql -h localhost -U postgres -d contract_intelligence \
		-c "SELECT id, clause_type, confidence, risk_level FROM clauses WHERE review_status = 'pending_review' LIMIT 20;"

# ============================================================================
# CI/CD SIMULATION
# ============================================================================

ci-check: lint test
	@echo "✓ CI checks passed"

ci-full: clean format lint test
	@echo "✓ Full CI pipeline passed"

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs:
	@echo "Building Sphinx documentation..."
	cd docs && make html
	@echo "✓ Documentation built: docs/_build/html/index.html"

docs-serve:
	@echo "Serving documentation at http://localhost:8001"
	python -m http.server 8001 --directory docs/_build/html

# ============================================================================
# QUICK START
# ============================================================================

quickstart: venv install db-init db-seed
	@echo ""
	@echo "✓ Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Activate virtual environment: source venv/bin/activate"
	@echo "  2. Start API: make api"
	@echo "  3. Or run demo: make demo"
	@echo ""
