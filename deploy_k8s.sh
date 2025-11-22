#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting Kubernetes Deployment...${NC}"

# 1. Check Tools
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed."
    exit 1
fi

# 2. Create Secrets
echo -e "${GREEN}Creating Secrets...${NC}"
# In a real setup, load these from a secure file or vault
kubectl create secret generic cv-secrets \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD=postgres \
  --from-literal=POSTGRES_DB=cv_matching \
  --from-literal=DATABASE_URL=postgresql://postgres:postgres@db:5432/cv_matching \
  --from-literal=SECRET_KEY=change_this_secret \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Apply Manifests
echo -e "${GREEN}Applying Manifests...${NC}"
kubectl apply -f infra/k8s/postgres.yaml
kubectl apply -f infra/k8s/ollama.yaml
kubectl apply -f infra/k8s/service.yaml
kubectl apply -f infra/k8s/deployment.yaml

# 4. Wait for Rollout
echo -e "${GREEN}Waiting for deployments...${NC}"
kubectl rollout status deployment/cv-job-matching-api
kubectl rollout status statefulset/db

echo -e "${GREEN}Deployment Complete!${NC}"
echo "Get service URL with: kubectl get svc cv-job-matching-api"
