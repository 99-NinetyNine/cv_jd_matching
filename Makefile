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

# Utility
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
