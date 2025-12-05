#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 CV-Job Matching System - Docker Compose Setup${NC}"

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Please create one first.${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Please install Docker first."
    exit 1
fi

# Use docker compose v2
DOCKER_COMPOSE="docker compose"

# Build and start services
echo -e "${GREEN}📦 Building and starting services...${NC}"
$DOCKER_COMPOSE -f infra/docker-compose.yml up -d --build

# Wait for database
echo -e "${GREEN}⏳ Waiting for database...${NC}"
sleep 10

# Initialize database
echo -e "${GREEN}🗄️  Initializing database...${NC}"
docker exec -i infra-db-1 psql -U postgres -d cv_matching < infra/init_db.sql

echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "API: http://localhost:8000"
echo -e "To view logs: $DOCKER_COMPOSE -f infra/docker-compose.yml logs -f"
