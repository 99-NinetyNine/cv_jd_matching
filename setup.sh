#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CV-Job Matching System Setup...${NC}"

# 1. Check Dependencies
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Force use of local standalone binary if it exists, as system version is broken
if [ -f "$HOME/.local/bin/docker-compose" ]; then
    DOCKER_COMPOSE="$HOME/.local/bin/docker-compose"
    echo "Using local docker-compose binary: $DOCKER_COMPOSE"
else
    # Try to download it if missing
    echo "Downloading docker-compose v2..."
    mkdir -p $HOME/.local/bin
    curl -SL https://github.com/docker/compose/releases/download/v2.29.1/docker-compose-linux-x86_64 -o $HOME/.local/bin/docker-compose
    chmod +x $HOME/.local/bin/docker-compose
    DOCKER_COMPOSE="$HOME/.local/bin/docker-compose"
    echo "Downloaded and using: $DOCKER_COMPOSE"
fi

echo "Docker Compose Version: $($DOCKER_COMPOSE version)"

# 2. Build and Start Services
echo -e "${GREEN}Building and starting services...${NC}"
$DOCKER_COMPOSE -f infra/docker-compose.yml up -d --build

# 3. Wait for Database
echo -e "${GREEN}Waiting for database to be ready...${NC}"
sleep 10

# 4. Initialize Database
echo -e "${GREEN}Initializing database...${NC}"
docker exec -i infra-db-1 psql -U postgres -d cv_matching < infra/init_db.sql

# 5. Frontend Setup (Optional, if running locally)
if [ -d "web" ]; then
    echo -e "${GREEN}Setting up frontend...${NC}"
    cd web
    npm install
    # We won't block on dev server, just tell user how to run it
    echo -e "${GREEN}Frontend dependencies installed.${NC}"
    cd ..
fi

echo -e "${GREEN}Setup Complete!${NC}"
echo "API is running at http://localhost:8000"
echo "To start the frontend, run: cd web && npm run dev"
