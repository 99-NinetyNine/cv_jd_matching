# Makefile for CV Matching System

.PHONY: up down build logs k8s-up k8s-down restart migration migrate db-current db-history db-check

# Docker Compose Commands
up:
	@echo "🚀 Starting Docker Compose..."
	docker-compose -f infra/docker-compose.yml up -d

down:
	@echo "🛑 Stopping Docker Compose..."
	docker-compose -f infra/docker-compose.yml down

build:
	@echo "🔨 Building Docker Images..."
	docker-compose -f infra/docker-compose.yml build

logs:
	@echo "📋 Tailing logs..."
	docker-compose -f infra/docker-compose.yml logs -f

restart: down up

# Kubernetes Commands
k8s-up:
	@echo "🚀 Deploying to Kubernetes..."
	./infra/k8s/start_k8s.sh

k8s-down:
	@echo "🛑 Removing Kubernetes Resources..."
	kubectl delete -f infra/k8s/
	kubectl delete secret cv-secrets --ignore-not-found

# Database Migration Commands
migration:
	@echo "📝 Creating new migration..."
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please provide a message with msg='your message'"; \
		echo "Example: make migration msg='add user preferences'"; \
		exit 1; \
	fi
	./venv/bin/alembic revision --autogenerate -m "$(msg)"

migrate:
	@echo "⬆️  Applying migrations..."
	./venv/bin/alembic upgrade head

db-current:
	@echo "📍 Current database version:"
	./venv/bin/alembic current

db-history:
	@echo "📜 Migration history:"
	./venv/bin/alembic history

db-check:
	@echo "🔍 Checking for schema drift..."
	./venv/bin/python scripts/check_schema.py

# Utility
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
