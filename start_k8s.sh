#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 CV-Job Matching System - Kubernetes Setup${NC}"

# Check and install kind if not present
if ! command -v kind &> /dev/null; then
    echo -e "${YELLOW}⚠️  kind not found. Installing kind...${NC}"
    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
    chmod +x ./kind
    echo -e "${GREEN}✅ kind installed locally (./kind)${NC}"
    KIND_CMD="./kind"
else
    KIND_CMD="kind"
    echo -e "${GREEN}✅ kind found${NC}"
fi

# Check if kind cluster exists, create if not
CLUSTER_NAME="cv-matching"
if ! $KIND_CMD get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${GREEN}📦 Creating local Kubernetes cluster...${NC}"
    $KIND_CMD create cluster --name ${CLUSTER_NAME}
else
    echo -e "${GREEN}✅ Cluster '${CLUSTER_NAME}' already exists${NC}"
fi

# Set kubectl context
kubectl config use-context kind-${CLUSTER_NAME}

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Please create one first.${NC}"
    exit 1
fi

# Load .env
echo -e "${GREEN}📄 Loading .env configuration...${NC}"
export $(cat .env | grep -v '^#' | xargs)

# Build Docker image for K8s
echo -e "${GREEN}🔨 Building Docker image...${NC}"
docker build -f infra/Dockerfile -t cv-matching-app:latest .

# Load image into kind cluster
echo -e "${GREEN}📥 Loading image into kind cluster...${NC}"
$KIND_CMD load docker-image cv-matching-app:latest --name ${CLUSTER_NAME}

# Create secrets from .env
echo -e "${GREEN}🔐 Creating Kubernetes secrets from .env...${NC}"
kubectl delete secret cv-secrets --ignore-not-found

kubectl create secret generic cv-secrets \
    --from-literal=DATABASE_URL="${DATABASE_URL}" \
    --from-literal=POSTGRES_USER="${POSTGRES_USER:-postgres}" \
    --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}" \
    --from-literal=POSTGRES_DB="${POSTGRES_DB:-cv_matching}"

# Apply manifests
echo -e "${GREEN}📦 Deploying to Kubernetes...${NC}"
kubectl apply -f infra/k8s/

# Wait for API service
echo -e "${GREEN}⏳ Waiting for API service...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/cv-matching-api

echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "API exposed at: http://localhost:8000"
echo -e ""
echo -e "Useful commands:"
echo -e "  kubectl get pods              # View pods"
echo -e "  kubectl top pods              # View CPU/RAM usage"
echo -e "  kubectl logs -f <pod-name>    # View logs"
echo -e "  kubectl get hpa               # View autoscaler status"
