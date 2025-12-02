# CV-Job Matching System - Scaling & Deployment Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Docker Compose Deployment](#docker-compose-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Periodic Task System](#periodic-task-system)
5. [Batch Processing Strategy](#batch-processing-strategy)
6. [Performance Optimization](#performance-optimization)
7. [Parsing Quality Evaluation](#parsing-quality-evaluation)
8. [Monitoring & Observability](#monitoring--observability)

---

## Architecture Overview

```
┌─────────────────┐
│   Load Balancer │
│     (Nginx)     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
┌───▼───┐ ┌──▼──┐  ┌───▼──┐   ┌───▼──┐
│ API 1 │ │API 2│  │API 3 │   │API N │  (Horizontal Scaling)
└───┬───┘ └──┬──┘  └───┬──┘   └───┬──┘
    │        │         │          │
    └────────┴─────────┴──────────┘
             │
    ┌────────▼──────────┐
    │   PostgreSQL      │
    │   + pgvector      │
    └───────────────────┘
             │
    ┌────────▼──────────┐
    │      Redis        │
    │  (Celery Broker)  │
    └────────┬──────────┘
             │
    ┌────────▼─────────────────────┐
    │  Celery Workers (Multiple)   │
    │  - CV Parsing                │
    │  - Embedding Computation     │
    │  - Match Generation          │
    │  - Explanation Generation    │
    └──────────────────────────────┘
             │
    ┌────────▼──────────┐
    │   Celery Beat     │
    │ (Task Scheduler)  │
    └───────────────────┘
```

---

## Docker Compose Deployment

### 1. Basic Setup

```bash
# Build and start all services
docker-compose up -d --build

# Scale API workers
docker-compose up -d --scale api=4

# Scale Celery workers
docker-compose up -d --scale celery-worker=6

# View logs
docker-compose logs -f api
docker-compose logs -f celery-worker
```

### 2. Production Configuration

**docker-compose.prod.yml**:
```yaml
version: '3.8'

services:
  api:
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  celery-worker:
    deploy:
      replicas: 8
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

Usage:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kubernetes Deployment

### 1. Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get svc
kubectl get hpa

# View logs
kubectl logs -f deployment/cv-matching-api
kubectl logs -f deployment/cv-matching-worker
```

### 2. Horizontal Pod Autoscaling

The system automatically scales based on CPU and memory:

**API Pods**: 3-10 replicas (scales at 70% CPU)
**Worker Pods**: 5-20 replicas (scales at 75% CPU)

```bash
# Check HPA status
kubectl get hpa

# Manual scaling
kubectl scale deployment cv-matching-api --replicas=6
kubectl scale deployment cv-matching-worker --replicas=12
```

### 3. Database Migration

```bash
# Run migrations in a pod
kubectl run alembic --rm -it --image=cv-matching-api:latest -- alembic upgrade head

# Or exec into existing pod
kubectl exec -it deployment/cv-matching-api -- alembic upgrade head
```

---

## Periodic Task System

### Overview

The system uses **Celery Beat** to schedule periodic tasks:

| Task | Frequency | Purpose |
|------|-----------|---------|
| `process_batch_cv_parsing` | Every 5 min | Parse pending CVs |
| `compute_pending_cv_embeddings` | Every 10 min | Compute CV embeddings |
| `compute_pending_job_embeddings` | Every 15 min | Compute job embeddings |
| `generate_matches_for_new_cvs` | Every 20 min | Generate job matches |
| `generate_batch_explanations` | Every 30 min | Generate explanations (RAG) |
| `retry_failed_embeddings` | Every hour | Retry failed items |
| `cleanup_old_data` | Daily 2 AM | Clean up old data |

### Task Flow

```
User Uploads CV
    ↓
[parsing_status = 'pending']
    ↓ (Every 5 min)
[Parse CV Task] → parsing_status = 'completed'
    ↓
[embedding_status = 'pending']
    ↓ (Every 10 min)
[Compute Embedding Task] → embedding_status = 'completed'
    ↓
[last_analyzed = NULL]
    ↓ (Every 20 min)
[Generate Matches Task] → Creates Prediction
    ↓
[matches without explanations]
    ↓ (Every 30 min)
[Generate Explanations Task] → Adds explanations
    ↓
[User sees complete results]
```

### Monitoring Tasks

```bash
# Check task status via Flower
http://localhost:5555

# Check Celery worker status
celery -A core.worker.celery_app status

# Inspect active tasks
celery -A core.worker.celery_app inspect active

# See scheduled tasks
celery -A core.worker.celery_app inspect scheduled
```

---

## Batch Processing Strategy

### Problem Statement

When **1000s of candidates** each upload **1 CV**, we need to:
1. Accept uploads quickly (don't block user)
2. Process in batches (efficient)
3. Return results eventually (async)

### Solution: Deferred Processing

#### Step 1: Upload (Immediate)
```python
# User uploads CV
POST /api/candidate/upload_and_parse

Response:
{
  "cv_id": "uuid",
  "status": "pending",  # Not parsed yet
  "message": "CV uploaded. Processing in background."
}
```

#### Step 2: Periodic Parsing (Every 5 min)
```python
# Celery task runs automatically
process_batch_cv_parsing()
- Finds CVs with parsing_status='pending'
- Parses up to 50 CVs per run
- Updates status to 'completed' or 'failed'
```

#### Step 3: Periodic Embedding (Every 10 min)
```python
compute_pending_cv_embeddings()
- Finds CVs with:
    parsing_status='completed'
    AND embedding_status='pending'
- Computes embeddings in batches
- Updates embedding_status='completed'
```

#### Step 4: Periodic Matching (Every 20 min)
```python
generate_matches_for_new_cvs()
- Finds CVs with:
    embedding_status='completed'
    AND (last_analyzed is NULL OR > 24 hours)
- Generates matches
- Saves Prediction records
- Caches results
```

#### Step 5: User Retrieves Results
```python
GET /api/candidate/recommendations

Response:
{
  "recommendations": [...],
  "prediction_id": "uuid",
  "count": 10
}
```

### Batch Size Optimization

```python
# tasks_enhanced.py

# Parse: 50 CVs per run (5 min interval = 600 CVs/hour)
pending_cvs = session.exec(...).limit(50)

# Embeddings: 100 items per run (10 min interval = 600/hour)
pending_cvs = session.exec(...).limit(100)

# Matches: 50 CVs per run (20 min interval = 150/hour)
cvs_needing_matches = session.exec(...).limit(50)
```

**Adjust based on your infrastructure**:
- More workers → increase batch size
- Slower embedding model → decrease batch size
- Higher API rate limits → increase batch size

---

## Performance Optimization

### 1. Database Optimizations

#### Indices (Already Applied)
```sql
-- Vector similarity (HNSW)
CREATE INDEX ON cv USING hnsw (embedding vector_cosine_ops);

-- Status filtering
CREATE INDEX ON cv (parsing_status);
CREATE INDEX ON cv (embedding_status);

-- Composite index for common queries
CREATE INDEX ON cv (embedding_status, is_latest, last_analyzed)
WHERE embedding_status = 'completed' AND is_latest = true;
```

#### Query Optimization
```python
# BAD: N+1 queries
for cv in cvs:
    matches = find_matches(cv)  # Separate query each time

# GOOD: Batch query with CROSS JOIN LATERAL
query = text("""
    SELECT c.id, j.job_id, 1 - (c.embedding <=> j.embedding) as similarity
    FROM cv c
    CROSS JOIN LATERAL (
        SELECT job_id, embedding
        FROM job
        WHERE embedding_status = 'completed'
        ORDER BY embedding <=> c.embedding
        LIMIT 10
    ) j
    WHERE c.id IN (:cv_ids)
""")
```

### 2. Vector Search Optimization

**HNSW Parameters**:
```sql
CREATE INDEX ON cv USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Adjust at query time:
SET hnsw.ef_search = 100;  -- Higher = more accurate, slower
```

**Trade-offs**:
- `m=16`: Good balance (12-24 range)
- `ef_construction=64`: Build time vs accuracy
- `ef_search=100`: Query time accuracy

### 3. Celery Optimizations

```python
# celery_app.py
celery_app.conf.update(
    worker_prefetch_multiplier=1,  # For long-running tasks
    worker_max_tasks_per_child=100,  # Restart worker (memory)
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Requeue on failure
)
```

### 4. Caching Strategy

```python
# Redis caching for frequent queries
cache_key = f"match_results:pgvector:{cv_id}"
cached = redis_client.get(cache_key)

if cached:
    return json.loads(cached)

# Compute and cache
matches = matcher.match(cv_data)
redis_client.set(cache_key, json.dumps(matches), ttl=3600)  # 1 hour
```

---

## Parsing Quality Evaluation

### Automatic Evaluation (No User Feedback Needed)

```bash
# Evaluate all CVs in tests/test_resumes/
python scripts/evaluate_parsing_quality.py

# Evaluate single CV
python scripts/evaluate_parsing_quality.py --cv path/to/resume.pdf
```

### Metrics Computed

1. **Schema Validation**
   - Field completeness (% of required fields populated)
   - Field type correctness

2. **Format Validation**
   - Email format (regex)
   - Phone format
   - Date formats (YYYY-MM-DD)
   - Date consistency (start < end)

3. **Cross-field Consistency**
   - No duplicate entries
   - Experience plausibility (< 50 years)

4. **Ground Truth Comparison** (if available)
   - Name match accuracy
   - Skills extraction Precision/Recall/F1
   - Field-level accuracy

### Example Output

```
📊 Aggregate Metrics (5 CVs)
   Average Completeness: 85.00%
   Email Validity: 100.00%
   Date Validity: 100.00%
   Average Skills F1: 78.50%

💾 Results saved to: parsing_evaluation_results.json
```

### Continuous Monitoring

```python
# Add to admin dashboard
@router.get("/admin/parsing_quality")
async def get_parsing_quality(session: Session):
    # Run evaluator on sample CVs
    evaluator = ParsingQualityEvaluator()
    results = evaluator.evaluate_batch()
    return results
```

---

## Monitoring & Observability

### 1. Health Checks

```bash
# System health
curl http://localhost:8000/api/admin/system_health

# Celery test
curl -X POST http://localhost:8000/api/admin/test_celery
```

### 2. Metrics Endpoints

```bash
# Performance metrics
curl http://localhost:8000/api/admin/performance_dashboard

# Evaluation metrics (CTR, conversion, etc.)
curl http://localhost:8000/api/admin/evaluation_metrics?days=30
```

### 3. Flower Dashboard

Access Celery monitoring UI:
```
http://localhost:5555
```

### 4. Database Monitoring

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 5. Logging

```python
# Structured logging
import logging

logger = logging.getLogger(__name__)
logger.info(f"Parsed CV {cv_id}", extra={
    "cv_id": cv_id,
    "duration_ms": duration,
    "fields_extracted": len(fields)
})
```

### 6. Alerts (Recommended)

Set up alerts for:
- High failure rate in parsing (> 10%)
- High embedding failure rate (> 5%)
- Database connection issues
- Redis connection issues
- Worker queue backlog (> 1000 tasks)
- P95 latency > 5 seconds

---

## Performance Targets & SLAs

| Metric | Target | Acceptable |
|--------|--------|------------|
| CV Parsing | < 3s | < 5s |
| Embedding Computation | < 1s | < 2s |
| Vector Search (10 results) | < 100ms | < 200ms |
| Match Generation (full) | < 2s | < 3s |
| Throughput (parsing) | > 600 CVs/hour | > 300 CVs/hour |
| Throughput (matching) | > 150 CVs/hour | > 75 CVs/hour |
| API Response Time (P95) | < 500ms | < 1s |

---

## Troubleshooting

### High CPU Usage

```bash
# Check active tasks
celery -A core.worker.celery_app inspect active

# Reduce concurrency
# In docker-compose.yml
command: celery -A core.worker.celery_app worker --concurrency=2
```

### High Memory Usage

```bash
# Restart workers after N tasks
# In docker-compose.yml
command: celery -A core.worker.celery_app worker --max-tasks-per-child=50
```

### Queue Backlog

```bash
# Check queue length
celery -A core.worker.celery_app inspect stats

# Scale up workers
kubectl scale deployment cv-matching-worker --replicas=15
```

### Database Slow Queries

```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Check for missing indices
SELECT * FROM pg_stat_user_tables WHERE idx_scan = 0;
```

---

## Cost Optimization

### 1. Use Mock Embeddings for Development

```bash
# Generate dummy data with mock embeddings (no API costs)
python scripts/generate_dummy_cvs.py --cvs 1000 --jobs 500
```

### 2. Token Management

```python
from core.utils.token_utils import TokenManager

tm = TokenManager()
truncated_text = tm.truncate_text(long_text, max_tokens=8000)
estimated_cost = tm.estimate_cost(input_tokens=10000, output_tokens=1000)
```

### 3. Batch API Calls

```python
# Instead of 100 separate calls
for cv in cvs:
    embedding = api.embed(cv.text)  # $$$

# Use batch embedding
texts = [cv.text for cv in cvs]
embeddings = api.embed_batch(texts)  # $
```

---

## Next Steps

1. **Set up monitoring** (Prometheus + Grafana)
2. **Configure alerting** (PagerDuty/Slack)
3. **Load test** with Locust
4. **Optimize batch sizes** based on infrastructure
5. **Set up CI/CD** pipeline
6. **Configure backups** (PostgreSQL, Redis)
7. **Implement A/B testing** for matching algorithms

---

## Quick Reference Commands

```bash
# Docker Compose
docker-compose up -d --scale api=4 --scale celery-worker=6
docker-compose logs -f celery-worker
docker-compose down

# Kubernetes
kubectl apply -f k8s/
kubectl get pods -w
kubectl logs -f deployment/cv-matching-api
kubectl scale deployment cv-matching-worker --replicas=10

# Celery
celery -A core.worker.celery_app worker --loglevel=info
celery -A core.worker.celery_app beat --loglevel=info
celery -A core.worker.celery_app flower

# Database
psql -U postgres -d cv_matching -f infra/init_db.sql
psql -U postgres -d cv_matching -c "SELECT COUNT(*) FROM cv WHERE parsing_status='pending';"

# Evaluation
python scripts/evaluate_parsing_quality.py
python scripts/generate_dummy_cvs.py --cvs 1000 --jobs 500

# Load Testing
locust -f scripts/locust_load_test.py --host=http://localhost:8000
```

---

**Happy Scaling! 🚀**
