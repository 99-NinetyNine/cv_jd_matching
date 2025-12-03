# Batch Testing Guide

This guide explains how to test batch operations without spending money on OpenAI API calls.

## Mock Batch Service

The **MockBatchService** simulates OpenAI's Batch API behavior for testing purposes.

### Features

✅ **Zero Cost** - No API calls, no charges
✅ **Instant Results** - Batches complete immediately (no 24h wait)
✅ **Realistic Behavior** - Simulates success/failure rates
✅ **File Storage** - Saves batches in `.mock_batches/` directory
✅ **All Endpoints** - Supports embeddings, parsing, and explanations

---

## How It Works

### 1. **Auto-Detection**

MockBatchService is automatically enabled when:
- `USE_MOCK_BATCH=true` environment variable is set
- OR `OPENAI_API_KEY` is not set (for testing environments)

```bash
# Enable mock mode
export USE_MOCK_BATCH=true

# Run tests
pytest tests/test_batch_operations.py
```

### 2. **File Storage Structure**

```
.mock_batches/
├── input_files/        # Uploaded batch request files
│   └── file_mock_abc123.jsonl
├── output_files/       # Generated batch results
│   └── file_mock_xyz789.jsonl
└── batch_metadata/     # Batch status tracking
    └── batch_mock_def456.json
```

⚠️ **Added to `.gitignore`** - These files are never committed

### 3. **Mock Response Generation**

The mock service generates realistic responses based on request type:

#### **Embeddings** (`/v1/embeddings`)
```json
{
  "custom_id": "cv-123",
  "response": {
    "body": {
      "data": [{
        "embedding": [0.1, -0.05, 0.03, ...]  // 768 dimensions
      }]
    }
  }
}
```

#### **CV Parsing** (`/v1/chat/completions` with "parse" in custom_id)
```json
{
  "custom_id": "cv-parse-123",
  "response": {
    "body": {
      "choices": [{
        "message": {
          "content": "{\"basics\": {...}, \"work\": [...], ...}"
        }
      }]
    }
  }
}
```

#### **Explanations** (`/v1/chat/completions` - other)
```json
{
  "custom_id": "pred-abc-job-123",
  "response": {
    "body": {
      "choices": [{
        "message": {
          "content": "This candidate is a great match because..."
        }
      }]
    }
  }
}
```

---

## Running Tests

### Basic Test Run
```bash
pytest tests/test_batch_operations.py -v
```

### Test Specific Features
```bash
# Test batch service
pytest tests/test_batch_operations.py::TestBatchService -v

# Test batch parsing
pytest tests/test_batch_operations.py::TestBatchParsing -v

# Test batch matching
pytest tests/test_batch_operations.py::TestBatchMatching -v

# Test mock responses
pytest tests/test_batch_operations.py::TestMockResponses -v

# Test scalability
pytest tests/test_batch_operations.py::TestScalability -v
```

### With Coverage
```bash
pytest tests/test_batch_operations.py --cov=core/services --cov=core/matching --cov=core/parsing
```

---

## Testing Real Batch Operations

### Option 1: Force Mock Mode
```python
from core.services.batch_service import BatchService

# Explicitly use mock
service = BatchService(use_mock=True)
```

### Option 2: Use Environment Variable
```bash
# In your shell or .env file
export USE_MOCK_BATCH=true

# Now all batch operations use mock
python your_script.py
```

### Option 3: Test with Real API (Optional)
```bash
# Set API key and disable mock
export OPENAI_API_KEY=sk-...
export USE_MOCK_BATCH=false

# Run tests (will use real API - costs money!)
pytest tests/test_batch_operations.py
```

---

## Test Coverage

The test suite covers:

### ✅ Batch Service Operations
- Creating batch files
- Uploading files
- Creating batches
- Retrieving batch status
- Retrieving results

### ✅ CV Parsing
- Batch parser initialization
- Preparing parsing requests
- Processing parsing results

### ✅ Embeddings
- CV embedding requests
- Job embedding requests
- Embedding result processing

### ✅ Batch Matching
- Finding CVs needing matches
- Performing vector search
- Creating predictions
- Submitting explanations

### ✅ Mock Responses
- Embedding generation (768D vectors)
- CV parsing (valid JSON Resume)
- Explanation generation

### ✅ Scalability
- Dynamic batch sizing
- Memory limits
- Batch size enforcement

---

## Failure Simulation

The mock service simulates a **5% failure rate** to test error handling:

```python
# In mock_batch_service.py
if random.random() < 0.05:
    batch.request_counts["failed"] += 1
    continue  # Skip this request
```

This ensures your code handles failures gracefully.

---

## Debugging

### View Mock Batch Files
```bash
# List all batches
ls -la .mock_batches/batch_metadata/

# View batch status
cat .mock_batches/batch_metadata/batch_mock_abc123.json

# View input requests
cat .mock_batches/input_files/file_mock_xyz789.jsonl

# View generated responses
cat .mock_batches/output_files/file_mock_def456.jsonl
```

### Enable Logging
```python
import logging
logging.basicConfig(level=logging.INFO)

# Now you'll see mock batch operations in logs
```

---

## Cleaning Up

### Manual Cleanup
```bash
rm -rf .mock_batches/
rm test_batch.db
```

### Automatic Cleanup
Tests automatically clean up mock files after completion (see fixtures in `test_batch_operations.py`)

---

## Real-World Simulation

### Batch Status Transitions

In reality, batches go through:
1. `validating` (checking input)
2. `in_progress` (processing)
3. `finalizing` (preparing output)
4. `completed` (done)

**Mock behavior:** Batches complete **immediately** to speed up tests.

To simulate delays (optional):
```python
import time

# After creating batch
batch = service.create_batch(...)
time.sleep(2)  # Simulate 2 second delay
status = service.retrieve_batch(batch.batch_api_id)
```

---

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Batch Tests
  env:
    USE_MOCK_BATCH: true
  run: |
    pytest tests/test_batch_operations.py -v
```

### Docker Example
```dockerfile
ENV USE_MOCK_BATCH=true
RUN pytest tests/test_batch_operations.py
```

---

## Troubleshooting

### Issue: Tests fail with "OpenAI client not initialized"
**Solution:** Set `USE_MOCK_BATCH=true` or remove `OPENAI_API_KEY` from environment

### Issue: Mock files persist between test runs
**Solution:** Tests should auto-clean, but you can manually run:
```bash
rm -rf .mock_batches/ test_batch.db
```

### Issue: Want to test real API occasionally
**Solution:**
```bash
export USE_MOCK_BATCH=false
export OPENAI_API_KEY=sk-...
pytest tests/test_batch_operations.py -k "test_specific_feature"
```

---

## Performance Comparison

| Operation | Real API | Mock API |
|-----------|----------|----------|
| Create batch | ~1 second | Instant |
| Process batch | 1-24 hours | Instant |
| Check status | ~500ms | Instant |
| Retrieve results | ~2 seconds | Instant |
| Cost per 1000 requests | $0.10-$5.00 | $0.00 |

**Mock API is ~10,000x faster and free!** 🚀

---

## Contributing

When adding new batch operations:

1. Add mock response generator in `mock_batch_service.py`
2. Write tests in `test_batch_operations.py`
3. Ensure tests pass in both mock and real modes
4. Update this guide with new features

---

## Questions?

Check the source code:
- [mock_batch_service.py](../core/services/mock_batch_service.py) - Mock implementation
- [batch_service.py](../core/services/batch_service.py) - Real/mock switcher
- [test_batch_operations.py](./test_batch_operations.py) - Test suite
