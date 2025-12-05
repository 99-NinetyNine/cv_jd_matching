# CV-Job Matching System

Production-ready CV-job matching platform with semantic vector search, LLM-based parsing, and batch processing. Handles 1000+ CVs and 500+ JDs concurrently with <4s matching latency.

## 🚀 Features

- **LLM-Based CV Parsing**: 91% field-level accuracy using LangGraph workflows with Chain-of-Thought reasoning
- **Semantic Vector Search**: pgvector HNSW indices for O(log n) similarity search
- **Batch Processing**: OpenAI Batch API integration (50% cost reduction)
- **Multi-Dimensional Matching**: Hybrid scoring (35% skills, 25% semantic, 25% experience, 15% education)
- **Real-Time Analysis**: WebSocket endpoints with token streaming
- **CV Quality Analyzer**: Standalone quality checker with 5 metrics
- **Admin Dashboard**: System health, performance metrics, batch management
- **Containerized Deployment**: Docker Compose and Kubernetes support

## 📋 Prerequisites

- **Python 3.10+**
- **Docker** and **Docker Compose** (recommended, though takes time for 1st time build)
- **PostgreSQL 16** with **pgvector** extension
- **Redis 7**
- **Ollama** (optional, for local embeddings)
- **API Keys**: OpenAI or Google Gemini (for production LLM calls)

## 🛠️ Installation

### Method 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone <repo-url>
cd cv

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start all services (one command does everything!)
./start.sh
```

The `start.sh` script automatically:
1. Builds Docker images
2. Starts PostgreSQL, Redis, Ollama, API, Celery Worker, Celery Beat
3. Initializes database tables with indices
4. Sets up pgvector extension

**Access Points:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173 (if web/ is started)

### Method 2: Local Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Setup PostgreSQL with pgvector
# (Install PostgreSQL 16 + pgvector extension manually)

# Setup Redis
# (Install Redis 7)

# Copy and configure environment
cp .env.example .env
nano .env

# Initialize database tables
python scripts/init_tables.py

# Start API server
uvicorn api.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A core.worker.celery_app worker --loglevel=info

# Start Celery beat (separate terminal)
celery -A core.worker.celery_app beat --loglevel=info

# (Optional) Start Ollama
ollama serve
ollama pull nomic-embed-text
```

## ⚙️ Environment Setup

### Required Environment Variables (.env)

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=cv_matching
DATABASE_URL=postgresql://postgres:postgres@db:5432/cv_matching

# LLM Configuration
USE_REAL_LLM=false  # Set to true for production
LLM_MODEL=llama3    # Options: llama3, gpt-4o, gemini-1.5-pro

# Ollama (for local dev)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# API Keys (required if USE_REAL_LLM=true)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# API Settings
API_PORT=8000
SECRET_KEY=change_this_in_production_secret_key_12345
```

See `.env.example` for all available options.

## 🗄️ Database Setup

### Automatic (Docker Compose)

When using `./start.sh`, the database is automatically initialized with:
- All tables (cv, job, prediction, userinteraction, batchjob, batchrequest, user)
- pgvector extension
- HNSW vector indices
- Composite and partial indices

### Manual (Local Development)

```bash
# Destroy existing tables and recreate (CAUTION: Data loss!)
python scripts/init_tables.py
```

This script:
1. Drops all existing tables
2. Creates tables with proper schemas
3. Sets up pgvector indices:
   ```sql
   CREATE INDEX idx_cv_embedding_hnsw ON cv
   USING hnsw (embedding vector_cosine_ops)
   WITH (m=16, ef_construction=64);

   CREATE INDEX idx_job_embedding_hnsw ON job
   USING hnsw (embedding vector_cosine_ops)
   WITH (m=16, ef_construction=64);
   ```

**Note**: Indices are created AFTER initial table creation. If using Docker Compose, check `docker-compose.yml` for the initialization order.

## 🏃 Running the System

### Docker Compose

```bash
# Start all services
./start.sh

# Stop all services
docker-compose -f infra/docker-compose.yml down

# View logs
docker-compose -f infra/docker-compose.yml logs -f api
docker-compose -f infra/docker-compose.yml logs -f celery-worker
docker-compose -f infra/docker-compose.yml logs -f celery-beat

# Restart specific service
docker-compose -f infra/docker-compose.yml restart api
```

### Local Development

```bash
# Terminal 1: API
uvicorn api.main:app --reload

# Terminal 2: Celery Worker
celery -A core.worker.celery_app worker --loglevel=info

# Terminal 3: Celery Beat
celery -A core.worker.celery_app beat --loglevel=info

# Terminal 4: Frontend (optional)
cd web && npm run dev
```

### Kubernetes

```bash
# Deploy to Kubernetes
./start_k8s.sh

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/api

# Scale workers
kubectl scale deployment/celery-worker --replicas=3
```

## 🧪 Testing with Sample Data

### 1. Create Admin User

```bash
# Docker
docker-compose -f infra/docker-compose.yml exec api python scripts/create_admin.py admin@test.com admin123

# Local
python scripts/create_admin.py admin@test.com admin123
```

### 2. Upload Sample Jobs

```bash
# Load 9 sample job descriptions from tests/test_job_desc/
python scripts/post_jobs_from_json.py
```

This script:
- Registers a random hirer account
- Loads all JSON files from `tests/test_job_desc/`
- Posts jobs via `/jobs` endpoint
- With `is_test=true`, embeddings are computed synchronously (using Ollama)

**Sample Jobs Included:**
- Procurement Manager (RWE AG)
- Software Engineer roles
- Teacher positions
- Advocate roles
- Business Development
- Designer positions
- IT roles

### 3. Upload Sample CVs and Generate Matches

```bash
# Upload CVs and get job recommendations
python scripts/upload_cvs_and_match.py
```

This script:
- Registers a random candidate account
- Loads all PDFs from `tests/test_resumes/` (5 sample CVs)
- Uploads each CV with `action=match`
- Performs CV parsing → embedding → vector search → match generation
- Saves recommendation results to `tests/test_predicted_results/`

**Sample CVs Included:**
- ADVOCATE_14445309.pdf
- BUSINESS-DEVELOPMENT_65708020.pdf
- DESIGNER_37058472.pdf
- INFORMATION-TECHNOLOGY_36856210.pdf
- TEACHER_12467531.pdf

### 4. Alternative: Upload CVs Only (No Matching)

```bash
# Upload CVs without immediate matching (batch processing later)
python scripts/upload_cvs.py
```

Uses `action=upload` to queue CVs for batch processing.

### 5. Run Load Tests (Performance Testing)

```bash
# Install Locust
pip install locust

# Run load test with web UI
locust -f tests/locustfile.py --host=http://localhost:8000

# Headless load test (100 users, 10/sec spawn, 5 min)
locust -f tests/locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s

# Test specific user flows
locust -f tests/locustfile.py --host=http://localhost:8000 CandidateUser
locust -f tests/locustfile.py --host=http://localhost:8000 HirerUser
locust -f tests/locustfile.py --host=http://localhost:8000 AdminUser
```

**Load Test Scenarios:**
- **CandidateUser**: Upload CV → Get recommendations → View jobs → Save/Apply
- **HirerUser**: Create job → List jobs → View applications → Shortlist/Interview/Hire
- **AdminUser**: Monitor evaluation metrics, performance dashboard, system health
- **MixedTraffic**: 70% candidates, 25% hirers, 5% admin (realistic traffic)
- **BurstTraffic**: Sudden spike in CV uploads
- **HeavyLoad**: Sustained high load

### 6. Evaluate Parsing Quality

```bash
# Evaluate CV parsing accuracy against ground truth
python scripts/evaluate_parsing_quality.py
```

Uses the evaluation framework from [Layout-Aware Parsing paper](https://arxiv.org/abs/2510.09722).

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - Register candidate/hirer/admin
- `POST /token` - Login (returns JWT token)

### Candidate Endpoints
- `POST /upload?action={upload|parse|match}` - Upload CV with action:
  - `upload`: Save only (batch processing later)
  - `parse`: Upload + parse synchronously
  - `match`: Upload + parse + match (full flow)
- `GET /recommendations` - Get job recommendations
- `POST /interactions/log` - Log viewed/saved/applied actions

### Hirer Endpoints
- `POST /jobs?is_test={true|false}` - Create job posting
  - `is_test=true`: Compute embedding synchronously (Ollama)
  - `is_test=false`: Queue for batch processing
- `GET /jobs` - List own jobs
- `GET /jobs/{job_id}/applications` - View applicants for job
- `POST /interactions/log` - Shortlist/interview/hire/reject

### Advanced Endpoints
- `WS /super-advanced/ws/analyze/{cv_id}` - Real-time CV analysis with streaming
- `WS /cv-quality/ws/analyze/{cv_id}` - CV quality check with token streaming

### Admin Endpoints
- `GET /admin/evaluation_metrics` - CTR, conversion rate, F1-score, precision, recall
- `GET /admin/performance_dashboard` - Parsing/embedding/matching throughput
- `GET /admin/system_health` - Service status, queue depths, error rates
- `GET /admin/batches` - View batch job status
- `POST /admin/trigger_batch` - Manual batch trigger

### Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🏗️ Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  FastAPI    │────▶│ PostgreSQL  │
│  (React)    │     │    API      │     │ + pgvector  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                           ├────────────────────▶│
                           │                     │
                    ┌──────┴──────┐       ┌──────┴──────┐
                    │   Redis     │       │   Ollama    │
                    │   Cache     │       │  (Local LLM)│
                    └─────────────┘       └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Celery    │
                    │   Worker    │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │Celery Beat  │
                    │ (Scheduler) │
                    └─────────────┘
```

## 🔄 Batch Processing Workflow

1. **CV Upload** → `parsing_status='batch_pending'`
2. **Celery Beat** triggers `process_batch_cv_parsing`
3. **Dynamic Batch Sizer** determines optimal batch size (100-500)
4. **Batch Submitted** to OpenAI Batch API
5. **Status Checker** polls completion every 60 seconds
6. **Parsing Complete** → `parsing_status='completed'`, `embedding_status='batch_pending'`
7. **Embedding Batch** created and submitted
8. **Embedding Complete** → `embedding_status='completed'`
9. **Batch Matcher** performs CROSS JOIN LATERAL vector search
10. **Predictions Created** with match scores
11. **Explanation Batch** generates human-readable justifications
12. **Results Cached** in Redis (6h TTL)

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
docker-compose -f infra/docker-compose.yml ps db

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Recreate database
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d db
python scripts/init_tables.py
```

### Celery Tasks Not Processing
```bash
# Check Celery worker is running
docker-compose -f infra/docker-compose.yml  ps celery-worker

# View Celery logs
docker-compose -f infra/docker-compose.yml  logs -f celery-worker

# Restart worker
docker-compose -f infra/docker-compose.yml restart celery-worker celery-beat
```

### Ollama Connection Failed
```bash
# Check Ollama is running
docker-compose -f infra/docker-compose.yml  ps ollama

# Pull embedding model
docker-compose -f infra/docker-compose.yml  exec ollama ollama pull nomic-embed-text

# Test embedding
curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test"}'
```

### HNSW Index Not Found
```bash
# Recreate indices
python scripts/init_tables.py

# Or manually via psql
docker-compose -f infra/docker-compose.yml exec db psql -U postgres -d cv_matching
CREATE INDEX idx_cv_embedding_hnsw ON cv USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_job_embedding_hnsw ON job USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
```

## 📚 Documentation

- **Technical Report**: [report.pdf](docs/report.pdf)
- **Sample Results**: [RESULTS.md](RESULTS.md)
- **API Docs**: http://localhost:8000/docs
- **CV Quality Feature**: [CV_QUALITY_FEATURE.md](docs/CV_QUALITY_FEATURE.md)
- **Advanced System**: [SUPER_ADVANCED_SYSTEM.md](docs/SUPER_ADVANCED_SYSTEM.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [JSON Resume Schema](https://jsonresume.org/) for standardized CV format
- [Layout-Aware Parsing paper](https://arxiv.org/abs/2510.09722) for evaluation framework
- [pgvector](https://github.com/pgvector/pgvector) for PostgreSQL vector search
- [LangGraph](https://github.com/langchain-ai/langgraph) for LLM workflows
- Kaggle community for sample resume and job datasets
