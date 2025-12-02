# Infrastructure Files

All deployment and configuration files for the CV-Job Matching System.

## Files Overview

### Core Files

#### `docker-compose.yml`
Complete multi-service Docker setup for local development and deployment.

**Services**:
- **api** (2 replicas) - FastAPI application
- **worker** (3 replicas) - Celery workers
- **beat** (1 replica) - Celery Beat scheduler (required for periodic tasks!)
- **flower** - Celery monitoring UI (http://localhost:5555)
- **db** - PostgreSQL with pgvector
- **redis** - Celery broker
- **ollama** - Embedding model
- **nginx** - Load balancer

**Start all services**:
```bash
cd infra
docker-compose up -d --build

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale api=4 --scale worker=6
```

**Stop services**:
```bash
docker-compose down
```

---

#### `Dockerfile`
Container image definition.

**Includes**:
- Python 3.11
- System dependencies (gcc, postgresql-client, tesseract, poppler)
- Python packages (requirements.txt + requirements_enhanced.txt)
- spaCy model (en_core_web_sm)

**Build**:
```bash
docker build -t cv-matching-api -f infra/Dockerfile .
```

---


#### `init_db.sql`
Database initialization script with 40+ performance indices.

**Includes**:
- HNSW vector indices for similarity search
- Status indices for filtering
- Composite indices for common queries
- GIN index for JSONB fields

**Apply manually**:
```bash
psql -U postgres -d cv_matching -f infra/init_db.sql
```

**Auto-applied**: Docker Compose automatically runs this on first start.

---

### Kubernetes (`k8s/`)

#### `cv-matching-deployment.yaml`
Complete Kubernetes deployment with auto-scaling.

**Resources**:
- API Deployment (3-10 pods, HPA enabled)
- Worker Deployment (5-20 pods, HPA enabled)
- Beat Deployment (1 pod)
- Redis Deployment
- Services (LoadBalancer, ClusterIP)
- PersistentVolumeClaim (50Gi for uploads)
- HorizontalPodAutoscalers

**Deploy**:
```bash
kubectl apply -f infra/k8s/cv-matching-deployment.yaml

# Check status
kubectl get pods
kubectl get hpa
kubectl get svc

# View logs
kubectl logs -f deployment/cv-matching-api
kubectl logs -f deployment/cv-matching-worker

# Scale manually
kubectl scale deployment cv-matching-api --replicas=6
kubectl scale deployment cv-matching-worker --replicas=12
```

**Delete**:
```bash
kubectl delete -f infra/k8s/cv-matching-deployment.yaml
```

---

#### Legacy Files (Keep for Reference)
- `deployment.yaml` - Old API deployment
- `postgres.yaml` - Old PostgreSQL config
- `ollama.yaml` - Old Ollama config
- `service.yaml` - Old service config

**Note**: Use `cv-matching-deployment.yaml` for new deployments.

---

## Quick Start

### Option 1: Docker Compose (Recommended for Development)

```bash
# 1. Start all services
cd infra
docker-compose up -d --build

# 2. Wait for services to be healthy (~2 minutes)
docker-compose ps

# 3. Check logs
docker-compose logs -f worker
docker-compose logs -f beat  # Important: periodic tasks!

# 4. Access services
# API: http://localhost:8000
# Flower: http://localhost:5555
# Nginx: http://localhost:80

# 5. Test Celery
curl -X POST http://localhost:8000/api/admin/test_celery

# 6. Stop services
docker-compose down
```

---

### Option 2: Kubernetes (Recommended for Production)

```bash
# 1. Create namespace (optional)
kubectl create namespace cv-matching
kubectl config set-context --current --namespace=cv-matching

# 2. Create secrets
kubectl create secret generic cv-matching-secrets \
  --from-literal=database-url='postgresql://user:pass@postgres:5432/cv_matching'

# 3. Deploy all resources
kubectl apply -f infra/k8s/cv-matching-deployment.yaml

# 4. Wait for pods to be ready
kubectl get pods -w

# 5. Check auto-scaling
kubectl get hpa

# 6. Access API
kubectl get svc api-service
# Use EXTERNAL-IP to access API

# 7. View logs
kubectl logs -f deployment/cv-matching-worker

# 8. Clean up
kubectl delete -f infra/k8s/cv-matching-deployment.yaml
```

---

## Environment Variables

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cv_matching
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=cv_matching

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# API
API_PORT=8000
SECRET_KEY=your-secret-key-here

# LLM (optional)
OPENAI_API_KEY=sk-...
```

---

## Troubleshooting

### Periodic tasks not running
**Problem**: Tasks in `/core/worker/tasks_enhanced.py` not executing
**Solution**: Ensure Celery Beat is running
```bash
docker-compose logs beat
# Should see: "beat: Starting..."
```

### Database connection failed
**Problem**: API can't connect to PostgreSQL
**Solution**: Check database is healthy
```bash
docker-compose ps db
# Should show: "healthy"

docker-compose logs db
```

### Ollama model not found
**Problem**: Embedding fails with "model not found"
**Solution**: Wait for ollama-init to complete
```bash
docker-compose logs ollama-init
# Should see: "pulling manifest" then "success"
```

### Port already in use
**Problem**: Can't start docker-compose
**Solution**: Change ports in docker-compose.yml
```yaml
ports:
  - "8001:8000"  # Use different port
```

---

## Monitoring

### Flower (Celery Monitoring)
http://localhost:5555

**Features**:
- Active tasks
- Worker status
- Task history
- Broker monitoring

### Docker Stats
```bash
docker stats
```

### Kubernetes Metrics
```bash
kubectl top pods
kubectl top nodes
```

---

## Performance Tuning

### Scale API Workers
```bash
# Docker Compose
docker-compose up -d --scale api=6

# Kubernetes
kubectl scale deployment cv-matching-api --replicas=8
```

### Scale Celery Workers
```bash
# Docker Compose
docker-compose up -d --scale worker=10

# Kubernetes
kubectl scale deployment cv-matching-worker --replicas=15
```

### Adjust Concurrency
Edit `docker-compose.yml`:
```yaml
worker:
  command: celery -A core.worker.celery_app worker --loglevel=info --concurrency=8
```

### Optimize Database
```bash
# Apply indices
psql -U postgres -d cv_matching -f infra/init_db.sql

# Check index usage
psql -U postgres -d cv_matching -c "SELECT * FROM pg_stat_user_indexes;"

# Vacuum
psql -U postgres -d cv_matching -c "VACUUM ANALYZE;"
```

---

## Files Checklist

- [x] `docker-compose.yml` - Multi-service setup
- [x] `Dockerfile` - Container image
- [x] `init_db.sql` - Database indices
- [x] `k8s/cv-matching-deployment.yaml` - Kubernetes deployment
- [x] `k8s/deployment.yaml` - Legacy (keep for reference)
- [x] `k8s/postgres.yaml` - Legacy (keep for reference)
- [x] `k8s/ollama.yaml` - Legacy (keep for reference)

---

## Next Steps

1. **Generate test data**:
   ```bash
   python scripts/generate_dummy_cvs.py --cvs 1000 --jobs 500
   ```

2. **Run load test**:
   ```bash
   locust -f scripts/locust_load_test.py --host=http://localhost:8000
   ```

3. **Check metrics**:
   ```bash
   curl http://localhost:8000/api/admin/performance_dashboard
   ```

4. **Evaluate parsing**:
   ```bash
   python scripts/evaluate_parsing_quality.py
   ```

---

For more details, see:
- **[SCALING_GUIDE.md](../SCALING_GUIDE.md)** - Complete deployment guide
- **[IMPLEMENTATION_NOTES.md](../IMPLEMENTATION_NOTES.md)** - Technical details
- **[FINAL_SUMMARY.md](../FINAL_SUMMARY.md)** - Overview

---

**Infrastructure ready for production deployment!** 🚀
