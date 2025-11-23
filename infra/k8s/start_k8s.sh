#!/bin/bash

# start_k8s.sh - Setup Secrets and Deploy to Kubernetes

echo "🚀 Starting Kubernetes Deployment..."

# 1. Load Environment Variables
if [ -f .env ]; then
    echo "📄 Loading configuration from .env file..."
    export $(cat .env | xargs)
else
    echo "⚠️  No .env file found. Using default/existing environment variables."
fi

# 2. Check for required variables (Add more as needed)
REQUIRED_VARS=("DATABASE_URL" "SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set. Please set it in .env or export it."
        exit 1
    fi
done

# 3. Create Secrets
echo "🔐 Creating Kubernetes Secrets..."
# Delete existing secret if it exists to allow update
kubectl delete secret cv-secrets --ignore-not-found

kubectl create secret generic cv-secrets \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}" \
    --from-literal=LLM_MODEL="${LLM_MODEL:-llama3}" \
    --from-literal=REDIS_HOST="${REDIS_HOST:-redis}" \
    --from-literal=REDIS_PORT="${REDIS_PORT:-6379}"

echo "✅ Secrets created."

# 4. Apply Manifests
echo "📦 Applying Kubernetes Manifests..."
kubectl apply -f infra/k8s/

echo "🎉 Deployment initiated! Check status with: kubectl get pods"
