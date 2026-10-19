# Common developer tasks. Run `make help` for the list.
# Python targets use the active interpreter; create a venv first:
#   python3.11 -m venv .venv && . .venv/bin/activate && make install

PYTHON ?= python3
IMAGE  ?= template-be-app:local

.DEFAULT_GOAL := help
.PHONY: help install dev down test lint fmt check build tf-validate scan

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install runtime + dev dependencies into the active environment
	$(PYTHON) -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt

dev: ## Start Postgres + Django with hot reload (docker compose)
	@test -f .env || cp .env.example .env
	docker compose up --build

down: ## Stop the local stack
	docker compose down

test: ## Run the pytest suite (SQLite, dev settings)
	cd backend && $(PYTHON) -m pytest -q

lint: ## Ruff lint
	cd backend && ruff check --config ../ruff.toml .

fmt: ## Ruff autofix
	cd backend && ruff check --config ../ruff.toml --fix .

check: ## Django system checks
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.dev $(PYTHON) manage.py check

build: ## Build the production image for linux/amd64
	docker build --platform linux/amd64 -t $(IMAGE) .

tf-validate: ## terraform fmt + validate without a backend or credentials
	cd terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false && terraform validate

scan: ## gitleaks over the git history
	gitleaks git --redact .
