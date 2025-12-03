"""
API Tests Suite
===============

This directory contains comprehensive tests for all API endpoints.

## Test Structure

```
tests/
├── conftest.py                    # Test fixtures and configuration
├── test_candidate_router.py       # Candidate endpoint tests
├── test_hirer_router.py          # Hirer endpoint tests
├── test_interactions_router.py   # Interaction endpoint tests
└── README.md                     # This file
```

## Test Coverage

### Candidate Endpoints (`test_candidate_router.py`)

**Upload CV (`POST /candidate/upload`)**
- ✅ Upload mode (file save only)
- ✅ Parse mode (file + parsing)
- ✅ Analyze mode (file + parsing + matching)
- ✅ Authentication required
- ✅ File type validation (PDF only)
- ✅ File size validation (max 5MB)
- ✅ Owner ID linking

**Get Recommendations (`GET /candidate/recommendations`)**
- ✅ Retrieve recommendations for authenticated user
- ✅ User-specific filtering (only own CVs)
- ✅ Latest CV selection
- ✅ Cache and database fallback
- ✅ Authentication required
- ✅ Error handling (no CV found)

### Hirer Endpoints (`test_hirer_router.py`)

**Create Job (`POST /jobs`)**
- ✅ Test mode (immediate embedding)
- ✅ Batch mode (queued embedding)
- ✅ Role-based authorization (hirer only)
- ✅ Owner ID linking
- ✅ Authentication required

**List Jobs (`GET /jobs`)**
- ✅ User sees only own jobs
- ✅ Admin can view all jobs (show_all=True)
- ✅ Non-admin cannot use show_all
- ✅ Authentication required

**Delete Job (`DELETE /jobs/{job_id}`)**
- ✅ Owner can delete own job
- ✅ Non-owner cannot delete
- ✅ Admin can delete any job
- ✅ Job not found handling
- ✅ Authentication required

**Get Job Applications (`GET /jobs/{job_id}/applications`)**
- ✅ Owner can view applications
- ✅ Non-owner cannot view
- ✅ Admin can view any job's applications
- ✅ Status filtering
- ✅ Candidate details included
- ✅ Authentication required

### Interaction Endpoints (`test_interactions_router.py`)

**Log Interaction (`POST /interactions/log`)**

*Candidate Actions:*
- ✅ viewed - Track job views
- ✅ saved - Bookmark jobs
- ✅ applied - Create application record

*Hirer Actions:*
- ✅ shortlisted - Mark for review
- ✅ interviewed - Track interview
- ✅ hired - Accept candidate (update application)
- ✅ rejected - Reject candidate (update application)

*Validation:*
- ✅ Action validation per user type
- ✅ Application creation on 'applied'
- ✅ Application status updates
- ✅ Duplicate application handling
- ✅ Authentication required

**Get User Stats (`GET /interactions/stats/{user_id}`)**
- ✅ User can view own stats
- ✅ User cannot view others' stats
- ✅ Admin can view any user's stats
- ✅ Empty stats handling
- ✅ Authentication required

**Get Job Stats (`GET /interactions/job/{job_id}/stats`)**
- ✅ Owner can view job stats
- ✅ Non-owner cannot view
- ✅ Admin can view any job's stats
- ✅ Engagement rate calculation
- ✅ Empty stats handling
- ✅ Job not found handling
- ✅ Authentication required

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_candidate_router.py
pytest tests/test_hirer_router.py
pytest tests/test_interactions_router.py
```

### Run Specific Test Class
```bash
pytest tests/test_candidate_router.py::TestUploadCV
pytest tests/test_hirer_router.py::TestCreateJob
```

### Run Specific Test
```bash
pytest tests/test_candidate_router.py::TestUploadCV::test_upload_cv_upload_mode_success
```

### Run with Coverage
```bash
pytest tests/ --cov=api.routers --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Print Statements
```bash
pytest tests/ -s
```

## Test Fixtures

### Database Fixtures
- `session` - Fresh in-memory database for each test
- `client` - FastAPI test client with database override

### User Fixtures
- `candidate_user` - Regular candidate user
- `premium_candidate_user` - Premium candidate user
- `hirer_user` - Hirer user
- `admin_user` - Admin user

### Auth Header Fixtures
- `candidate_auth_headers` - Auth headers for candidate
- `premium_candidate_auth_headers` - Auth headers for premium candidate
- `hirer_auth_headers` - Auth headers for hirer
- `admin_auth_headers` - Auth headers for admin

### Data Fixtures
- `sample_cv` - Test CV record
- `sample_job` - Test job record

## Key Features Tested

### Authentication & Authorization
- ✅ All endpoints require authentication
- ✅ Role-based access control (candidate, hirer, admin)
- ✅ Owner-based authorization (users can only access their own data)
- ✅ Admin override (admins can access all data)

### Data Ownership
- ✅ CVs are linked to candidate owners
- ✅ Jobs are linked to hirer owners
- ✅ Users can only see/modify their own data
- ✅ Proper filtering by owner_id

### Business Logic
- ✅ Application lifecycle (pending → accepted/rejected)
- ✅ Interaction tracking for analytics
- ✅ Engagement metrics calculation
- ✅ Duplicate handling

### Error Handling
- ✅ 401 for unauthenticated requests
- ✅ 403 for unauthorized access
- ✅ 404 for not found resources
- ✅ 400 for validation errors
- ✅ Helpful error messages

## Dependencies

Required packages (install with `pip install -r requirements.txt`):
- pytest
- pytest-cov (for coverage reports)
- httpx (for real API client)

## Notes

### Real API Testing (DEFAULT)
**All tests now hit the REAL API running in Docker by default.**

- **Client**: Uses `httpx.Client` to make HTTP requests to `http://localhost:8000`
- **Database**: Uses real PostgreSQL database at `localhost:5432`
- **Services**: Tests use actual parsing, matching, and caching services
- **Cleanup**: Test data is automatically cleaned up after each test

**Prerequisites:**
1. Start the API in Docker: `docker-compose up -d`
2. Ensure the API is running on `http://localhost:8000`
3. Ensure PostgreSQL is accessible at `localhost:5432`

### Legacy Unit Testing
For unit tests that need to mock dependencies, use the `unit_test_client` fixture:
```python
def test_something(unit_test_client, mocker):
    mocker.patch("some.dependency")
    response = unit_test_client.get("/endpoint")
```

### Database
Tests use the **real PostgreSQL database** running in Docker.
- Connection: `postgresql://postgres:postgres@localhost:5432/cv_matching`
- Data is cleaned up after each test to ensure isolation
- All test users have unique emails with UUID suffixes

### Test Data
Test data is created using fixtures in `conftest.py`.
Each test gets fresh data with automatic cleanup to prevent interference.

### Environment Variables
- `API_BASE_URL`: Base URL for API (default: `http://localhost:8000`)
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/cv_matching`)

## Future Enhancements

Potential areas for additional testing:
- [ ] WebSocket endpoints
- [ ] Batch processing workflows
- [ ] Rate limiting
- [ ] File upload edge cases
- [ ] Concurrent request handling
- [ ] Performance/load testing
"""

# This file serves as documentation
# The actual README content is in the docstring above
