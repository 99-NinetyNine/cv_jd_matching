.PHONY: up down restart build logs ps shell-api shell-db help

COMPOSE_FILE := infra/docker-compose.yml
COMPOSE := docker-compose -f $(COMPOSE_FILE)

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make up         Start services in background'
	@echo '  make down       Stop services'
	@echo '  make restart    Restart services'
	@echo '  make build      Rebuild services'
	@echo '  make logs       Tail logs'
	@echo '  make ps         Show service status'
	@echo '  make shell-api  Open shell in API container'
	@echo '  make shell-db   Open psql shell in DB container'

up: ## Start services
	$(COMPOSE) up -d

down: ## Stop services
	$(COMPOSE) down

restart: down up ## Restart services

build: ## Rebuild services
	$(COMPOSE) build

logs: ## Tail logs
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

shell-api: ## Open shell in API container
	$(COMPOSE) exec api bash

shell-db: ## Open psql shell in DB container
	$(COMPOSE) exec db psql -U postgres -d cv_matching
