# Database & Cache Access Guide

## PostgreSQL (pgvector)

You can access the database directly inside the Docker container.

### 1. Connect to Database
```bash
docker-compose -f infra/docker-compose.yml exec db psql -U postgres -d cv_matching
```

### 2. Common Queries

**List all tables:**
```sql
\dt
```

**View Jobs (and check embeddings):**
```sql
SELECT job_id, title, company, substring(description, 1, 50) as desc_preview, 
       (embedding IS NOT NULL) as has_embedding 
FROM job;
```

**View CVs:**
```sql
SELECT id, filename, (embedding IS NOT NULL) as has_embedding 
FROM cv;
```

**Check Vector Extension:**
```sql
\dx vector
```

**Simple Vector Search (Example):**
```sql
-- Find jobs similar to a specific job (by ID)
WITH job_emb AS (SELECT embedding FROM job WHERE job_id = 'YOUR_JOB_ID')
SELECT title, company, 1 - (embedding <=> (SELECT embedding FROM job_emb)) as similarity
FROM job
ORDER BY similarity DESC
LIMIT 5;
```

---

## Redis (Cache)

Inspect cached embeddings and match results.

### 1. Connect to Redis
```bash
docker compose -f infra/docker-compose.yml exec redis redis-cli
```

### 2. Common Commands

**List all keys:**
```redis
KEYS *
```

**Check specific key type:**
```redis
TYPE match_results:pgvector:YOUR_CV_ID
```

**Get value:**
```redis
GET match_results:pgvector:YOUR_CV_ID
```
