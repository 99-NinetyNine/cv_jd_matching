# Load Testing Guide for CV-Job Matching System

## Overview

This load testing suite uses [Locust](https://locust.io/) to simulate realistic user flows for the CV-Job matching system.

## Realistic Flow

```
1. Hirer creates job (synchronous)
2. Candidate uploads CV (synchronous: upload + parse + match)
3. Candidate gets recommendations (depends on available matches)
4. Candidate interacts: view → save → apply
5. Hirer reviews applications: shortlist → interview → hire/reject
6. Admin monitors logs (anytime)
```

## Installation

```bash
pip install locust
```

## Running Tests

### 1. Web UI (Interactive)

```bash
locust -f tests/locustfile.py --host=http://localhost:8000
```

Then open [http://localhost:8089](http://localhost:8089) in your browser.

### 2. Headless Mode (Automated)

```bash
# 100 users, spawn 10/sec, run for 5 minutes
locust -f tests/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 100 \
    -r 10 \
    -t 300s
```

### 3. Specific User Flow

Test only **candidates**:
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 CandidateUser
```

Test only **hirers**:
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 HirerUser
```

Test only **admin** monitoring:
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 AdminUser
```

### 4. Mixed Traffic (Realistic Simulation)

```bash
# 70% candidates, 25% hirers, 5% admin
locust -f tests/locustfile.py --host=http://localhost:8000 MixedTraffic
```

### 5. Load Scenarios

**Burst Traffic** (sudden spike):
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 BurstTraffic
```

**Heavy Sustained Load**:
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 HeavyLoad
```

## User Classes

### CandidateFlow (SequentialTaskSet)

Simulates realistic candidate journey:

1. **Register/Login** (auto)
2. **Upload CV** → `/candidate/upload?action=match`
   - Uploads PDF
   - Parses CV (synchronous)
   - Gets job matches immediately
   - Stores: `cv_id`, `prediction_id`, `recommendations`
3. **Get Recommendations** → `/candidate/recommendations`
   - May use cache or compute
   - Retrieves saved/applied jobs
4. **View Jobs** → `/interactions/log` (action: "viewed")
   - Logs view interaction for top 3 recommendations
5. **Save/Apply** → `/interactions/log` (action: "saved" or "applied")
   - 66% save, 33% apply
   - Creates Application record for "applied"

### HirerFlow (SequentialTaskSet)

Simulates realistic hirer journey:

1. **Register/Login** (auto)
2. **Create Job** → `/jobs?is_test=true`
   - Posts job with sample data
   - Computes embedding synchronously
   - Stores: `job_id`
3. **List Jobs** → `/jobs`
   - Views own job postings
4. **View Applications** → `/jobs/{job_id}/applications`
   - Gets candidate applications
5. **Take Action** → `/interactions/log` (action: "shortlisted", "interviewed", "hired", "rejected")
   - Updates Application status

### AdminUser

Monitors system health:

1. `/admin/evaluation_metrics` - CTR, conversion rates, quality metrics
2. `/admin/performance_dashboard` - Response times, throughput, DB latency
3. `/admin/system_health` - Component health, pending work

## API Endpoints Tested

### Authentication
- `POST /auth/register` - User registration
- `POST /token` - Login

### Candidate
- `POST /candidate/upload?action=match` - Upload CV (with full processing)
- `GET /candidate/recommendations` - Get job recommendations

### Hirer
- `POST /jobs?is_test=true` - Create job (with immediate embedding)
- `GET /jobs` - List own jobs
- `GET /jobs/{job_id}/applications` - View applications

### Interactions
- `POST /interactions/log` - Log user interactions (view, save, apply, shortlist, etc.)

### Admin
- `GET /admin/evaluation_metrics` - System evaluation metrics
- `GET /admin/performance_dashboard` - Performance metrics
- `GET /admin/system_health` - System health

## Authentication

All users automatically register/login on start. The script:
1. Tries to register with `load_test_{role}_{random}@example.com`
2. If exists, logs in
3. Stores JWT token in `Authorization: Bearer {token}` header
4. All subsequent requests use authenticated headers

## Metrics Reported

Locust tracks:
- **Requests**: Total, success, failures
- **Response Time**: Average, median, p50, p95, p99
- **Throughput**: Requests per second
- **Errors**: HTTP status codes, exceptions

## Sample Test Scenarios

### Scenario 1: Basic Load Test (100 users, 5 min)

```bash
locust -f tests/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 100 \
    -r 10 \
    -t 300s \
    MixedTraffic
```

### Scenario 2: Spike Test (0→500 users in 30s)

```bash
locust -f tests/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 500 \
    -r 20 \
    -t 300s \
    BurstTraffic
```

### Scenario 3: Endurance Test (50 users, 30 min)

```bash
locust -f tests/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 50 \
    -r 5 \
    -t 1800s \
    MixedTraffic
```

### Scenario 4: Candidate-Only Load (200 users)

```bash
locust -f tests/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 200 \
    -r 20 \
    -t 600s \
    CandidateUser
```

## Monitoring During Tests

1. **Locust Web UI**: http://localhost:8089 (real-time graphs)
2. **API Logs**: Check FastAPI logs
3. **Admin Dashboard**: http://localhost:8000/admin/performance_dashboard
4. **Database**: Monitor query performance

## Expected Behavior

### Synchronous Operations (Fast)
- Job creation: < 500ms
- CV upload + parse: < 2000ms
- CV upload + parse + match: < 5000ms

### Cached Operations (Very Fast)
- Get recommendations (cached): < 100ms
- List jobs: < 200ms

### Database Operations
- Log interaction: < 50ms
- View applications: < 300ms

## Troubleshooting

### Issue: 401 Unauthorized
**Cause**: Auth token expired or invalid
**Fix**: Script auto-refreshes, but check `/auth/register` and `/token` endpoints

### Issue: 404 No CV found
**Cause**: CV not uploaded yet or embedding not complete
**Fix**: Ensure `action=match` for full processing

### Issue: High failure rate on `/candidate/upload`
**Cause**: PDF parsing issues or database connection
**Fix**: Check PDF validity, database connection, and parsing service

### Issue: No recommendations returned
**Cause**: No jobs in database or embeddings not computed
**Fix**: Run `HirerFlow` first to create jobs, or seed database

## Advanced Usage

### Custom Load Pattern

Edit `locustfile.py` and modify task weights:

```python
class CustomFlow(HttpUser):
    wait_time = between(1, 3)
    tasks = {
        CandidateFlow: 80,  # 80% candidates
        HirerFlow: 20,      # 20% hirers
    }
```

### Adding Custom Metrics

```python
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    if "Upload CV" in name:
        print(f"CV upload took {response_time}ms")
```

## CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run Load Test
  run: |
    locust -f tests/locustfile.py \
      --host=http://localhost:8000 \
      --headless \
      -u 50 \
      -r 5 \
      -t 60s \
      --csv=load_test_results
```

## Performance Benchmarks

Based on expected system performance:

| Metric | Target | Good | Poor |
|--------|--------|------|------|
| Success Rate | > 99% | > 95% | < 95% |
| Avg Response Time | < 500ms | < 1000ms | > 1000ms |
| p95 Response Time | < 2000ms | < 3000ms | > 3000ms |
| RPS (50 users) | > 10 | > 5 | < 5 |
| CV Upload+Match | < 5000ms | < 8000ms | > 8000ms |
| Get Recs (cached) | < 100ms | < 300ms | > 300ms |

## Sample Output

```
============================================================
🚀 CV-Job Matching Load Test Starting
   Host: http://localhost:8000
   Realistic flow: Job Creation → CV Upload → Matching → Interactions
============================================================

[2025-12-04 10:00:00] INFO: ✓ Registered candidate: load_test_candidate_1234@example.com
[2025-12-04 10:00:01] INFO: ✓ CV uploaded: abc-123, got 5 recs
[2025-12-04 10:00:02] INFO: ✓ Got 5 recommendations

============================================================
✅ Load Test Completed!
============================================================
Total requests:        2450
Total failures:        12
Success rate:          99.51%
Avg response time:     342.67ms
Median response time:  210.00ms
95th percentile:       1200.50ms
99th percentile:       2800.30ms
Requests per second:   8.17
============================================================
```

## Next Steps

1. **Optimize slow endpoints** based on p95/p99 metrics
2. **Scale database** if query latency > 100ms
3. **Add caching** for frequently accessed data
4. **Monitor resource usage** (CPU, memory, DB connections)
5. **Run endurance tests** to detect memory leaks
