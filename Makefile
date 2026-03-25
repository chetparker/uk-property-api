# =============================================================================
# Makefile — Shortcut Commands
# =============================================================================
# A Makefile lets you type short commands instead of remembering long ones.
#
# Usage:
#   make install    — Install all Python packages
#   make dev        — Start the server locally (with auto-reload)
#   make test       — Run all unit tests
#   make lint       — Check code style
#   make deploy     — Deploy to Railway
#   make clean      — Remove temporary files
#   make help       — Show all available commands
#
# IMPORTANT: Makefile commands MUST use tabs (not spaces) for indentation.
# If you edit this file, make sure your editor uses real tabs.
# =============================================================================

# Use bash for shell commands (more features than plain sh).
SHELL := /bin/bash

# The default command when you just type "make" with no arguments.
.DEFAULT_GOAL := help

# These are not real files — they're just command names.
.PHONY: install dev test lint deploy clean help docker-dev

# -----------------------------------------------------------------------------
# Installation
# -----------------------------------------------------------------------------

install: ## Install all Python dependencies
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Done! Run 'make dev' to start the server."

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------

dev: ## Start the dev server with auto-reload (restarts when you save a file)
	@echo "🚀 Starting development server on http://localhost:8000"
	@echo "📖 API docs at http://localhost:8000/docs"
	@echo "Press Ctrl+C to stop."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-no-reload: ## Start the dev server WITHOUT auto-reload
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

test: ## Run all unit tests with verbose output
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --tb=short
	@echo "✅ Tests complete."

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	pip install coverage --quiet
	python -m coverage run -m pytest tests/ -v --tb=short
	python -m coverage report --show-missing
	@echo "✅ Coverage report complete."

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------

lint: ## Check code style with ruff (fast Python linter)
	@echo "🔍 Checking code style..."
	pip install ruff --quiet
	ruff check app/ tests/
	@echo "✅ Linting complete."

format: ## Auto-format code with ruff
	pip install ruff --quiet
	ruff format app/ tests/
	@echo "✅ Formatting complete."

# -----------------------------------------------------------------------------
# Deployment
# -----------------------------------------------------------------------------

deploy: test ## Deploy to Railway (runs tests first — won't deploy if tests fail)
	@echo "🚂 Deploying to Railway..."
	@echo "⚠️  Make sure you've run 'railway login' and 'railway link' first."
	railway up
	@echo "✅ Deployed! Check your Railway dashboard for the URL."

deploy-skip-tests: ## Deploy to Railway without running tests (use with caution)
	@echo "🚂 Deploying to Railway (skipping tests)..."
	railway up

# -----------------------------------------------------------------------------
# Docker (optional — for local development with Redis)
# -----------------------------------------------------------------------------

docker-dev: ## Start the app + Redis locally using Docker Compose
	@echo "🐳 Starting with Docker Compose..."
	docker compose up --build

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean: ## Remove temporary files and caches
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	@echo "✅ Clean."

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------

help: ## Show this help message
	@echo ""
	@echo "UK Property Data API — Available Commands:"
	@echo "============================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
