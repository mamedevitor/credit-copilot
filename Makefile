# Shortcuts for common project tasks. Run `make help` to list them.

COMP := home-credit-credit-risk-model-stability
RAW  := data/raw/home-credit-crms

.PHONY: help install data up down logs lint format test check

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies from uv.lock
	uv sync

data: ## Download the Kaggle data (accept the competition rules first)
	uv run python scripts/download_data.py --competition $(COMP) --dest $(RAW)

up: ## Start Postgres (pgvector) and MLflow
	docker compose up -d

down: ## Stop services (data is kept)
	docker compose down

logs: ## Follow service logs (Ctrl+C to exit)
	docker compose logs -f

lint: ## Check code style and errors
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format code and fix what ruff can fix
	uv run ruff format .
	uv run ruff check --fix .

test: ## Run the test suite
	uv run pytest

check: lint test ## Lint + tests (same as CI)
