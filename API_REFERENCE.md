# 📚 API Reference

Complete API documentation for the SQS Search Segmenter service.

---

## Base URL

```
http://localhost:8080
```

---

## 🏠 System Endpoints

### GET `/`

Get service information.

**Response:**
```json
{
  "service": "SQS Search Segmenter",
  "version": "1.0.0",
  "status": "running",
  "sqs_consumer": "active",
  "docs": "/docs",
  "health": "/health"
}
```

---

### GET `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "sqs_consumer_running": true,
  "components": {
    "api": "up",
    "sqs_consumer": "up"
  }
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service has issues

---

## 💼 Job Management (`/jobs`)

### POST `/jobs/create`

Create a new segmentation job and enqueue it to SQS.

**Request Body:**
```json
{
  "manifestation_id": "string",
  "total_segments": 10  // Optional - will be calculated if not provided
}
```

**Example:**
```bash
curl -X POST "http://localhost:8080/jobs/create" \
  -H "Content-Type: application/json" \
  -d '{
    "manifestation_id": "test-manifestation-001"
  }'
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "test-manifestation-001",
  "total_segments": 10,
  "status": "QUEUED",
  "message": "Job created and enqueued successfully. MessageId: abc123..."
}
```

**Status Codes:**
- `200 OK` - Job created successfully
- `400 Bad Request` - Invalid request data
- `500 Internal Server Error` - Server error

---

### GET `/jobs/{job_id}/status`

Get the current status and progress of a job.

**Path Parameters:**
- `job_id` (string, required) - UUID of the job

**Example:**
```bash
curl "http://localhost:8080/jobs/550e8400-e29b-41d4-a716-446655440000/status"
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "test-manifestation-001",
  "status": "IN_PROGRESS",
  "total_segments": 10,
  "completed_segments": 5,
  "progress_percentage": 50.0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "tasks": [
    {
      "task_id": "660f9511-f39c-52e5-b827-557766551111",
      "manifestation_id": "test-manifestation-001",
      "status": "COMPLETED",
      "error_message": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

**Job Status Values:**
- `QUEUED` - Job created, waiting for processing
- `IN_PROGRESS` - Job is being processed
- `COMPLETED` - Job finished successfully
- `FAILED` - Job failed (check error_message)

**Status Codes:**
- `200 OK` - Job found
- `404 Not Found` - Job not found
- `500 Internal Server Error` - Server error

---

### GET `/jobs/{job_id}/results`

Get the results of a completed job.

**Path Parameters:**
- `job_id` (string, required) - UUID of the job

**Example:**
```bash
curl "http://localhost:8080/jobs/550e8400-e29b-41d4-a716-446655440000/results"
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "test-manifestation-001",
  "status": "COMPLETED",
  "results": [
    {
      "task_id": "660f9511-f39c-52e5-b827-557766551111",
      "manifestation_id": "test-manifestation-001",
      "result_json": [
        {
          "search_segment_id": "seg-001",
          "search_segment_content": "Sample text content",
          "span_start": 0,
          "span_end": 19,
          "segments": [
            {
              "segment_id": "overlap-001",
              "segment_content": "Sample text",
              "span_start": 0,
              "span_end": 11
            }
          ]
        }
      ],
      "result_location": null
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Results retrieved
- `400 Bad Request` - Job not completed yet
- `404 Not Found` - Job not found
- `500 Internal Server Error` - Server error

---

## 🔍 Segmentation Results (`/segmentation`)

### GET `/segmentation/{manifestation_id}/segments`

Get all processed segments for a manifestation from the most recent completed job.

**Path Parameters:**
- `manifestation_id` (string, required) - ID of the manifestation

**Example:**
```bash
curl "http://localhost:8080/segmentation/test-manifestation-001/segments"
```

**Response:** `200 OK`
```json
{
  "manifestation_id": "test-manifestation-001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_segments": 10,
  "completed_segments": 10,
  "results": [
    {
      "search_segment_id": "seg-001",
      "search_segment_content": "Sample text content",
      "span_start": 0,
      "span_end": 19,
      "segments": [
        {
          "segment_id": "overlap-001",
          "segment_content": "Sample text",
          "span_start": 0,
          "span_end": 11
        }
      ]
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Segments retrieved
- `404 Not Found` - No completed job found for manifestation
- `500 Internal Server Error` - Server error

---

### GET `/segmentation/{manifestation_id}/neo4j-segments`

Get raw segment data directly from Neo4j (for debugging/setup).

**Path Parameters:**
- `manifestation_id` (string, required) - ID of the manifestation

**Example:**
```bash
curl "http://localhost:8080/segmentation/test-manifestation-001/neo4j-segments"
```

**Response:** `200 OK`
```json
{
  "manifestation_id": "test-manifestation-001",
  "expression_id": "expr-001",
  "annotation_id": "annot-001",
  "segments_count": 10,
  "segments": [
    {
      "search_segment_id": "seg-001",
      "span_start": 0,
      "span_end": 19
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Data retrieved
- `500 Internal Server Error` - Neo4j error or server error

---

## 🔄 Typical Workflow

### 1. Create a Job

```bash
# Create job
RESPONSE=$(curl -s -X POST "http://localhost:8080/jobs/create" \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "M001"}')

# Extract job_id
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"
```

### 2. Poll for Status

```bash
# Check status
while true; do
  STATUS=$(curl -s "http://localhost:8080/jobs/$JOB_ID/status" | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "COMPLETED" ] || [ "$STATUS" = "FAILED" ]; then
    break
  fi
  
  sleep 5
done
```

### 3. Get Results

```bash
# Get results when completed
curl "http://localhost:8080/jobs/$JOB_ID/results" | jq '.'

# Or get by manifestation ID
curl "http://localhost:8080/segmentation/M001/segments" | jq '.'
```

---

## 📊 Response Models

### Job Status Response

```typescript
{
  job_id: string (UUID)
  manifestation_id: string
  status: "QUEUED" | "IN_PROGRESS" | "COMPLETED" | "FAILED"
  total_segments: number
  completed_segments: number
  progress_percentage: number
  created_at: string (ISO 8601)
  updated_at: string (ISO 8601)
  tasks: Task[]
}
```

### Task Model

```typescript
{
  task_id: string (UUID)
  manifestation_id: string
  status: "QUEUED" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "RETRYING"
  error_message: string | null
  created_at: string (ISO 8601)
  updated_at: string (ISO 8601)
}
```

### Segment Result Model

```typescript
{
  search_segment_id: string
  search_segment_content: string
  span_start: number
  span_end: number
  segments: OverlappingSegment[]
}
```

### Overlapping Segment Model

```typescript
{
  segment_id: string
  segment_content: string
  span_start: number
  span_end: number
}
```

---

## 🔐 Authentication

Currently, the API does not implement authentication. For production use, you should add:

- API Keys
- JWT tokens
- OAuth 2.0
- IAM roles (for AWS deployments)

---

## ⚠️ Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

- `400 Bad Request` - Invalid input data
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

---

## 🧪 Testing with cURL

### Complete Test Sequence

```bash
# 1. Check health
curl http://localhost:8080/health

# 2. Create job
curl -X POST "http://localhost:8080/jobs/create" \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "M001"}'

# 3. Check status (replace JOB_ID)
curl "http://localhost:8080/jobs/JOB_ID/status"

# 4. Get results when completed
curl "http://localhost:8080/jobs/JOB_ID/results"

# 5. Get by manifestation
curl "http://localhost:8080/segmentation/M001/segments"

# 6. Get Neo4j data (debugging)
curl "http://localhost:8080/segmentation/M001/neo4j-segments"
```

---

## 🐍 Testing with Python

```python
import requests
import time

BASE_URL = "http://localhost:8080"

# Create job
response = requests.post(
    f"{BASE_URL}/jobs/create",
    json={"manifestation_id": "M001"}
)
job_id = response.json()["job_id"]
print(f"Created job: {job_id}")

# Poll for completion
while True:
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
    status = response.json()["status"]
    progress = response.json()["progress_percentage"]
    
    print(f"Status: {status}, Progress: {progress}%")
    
    if status in ["COMPLETED", "FAILED"]:
        break
    
    time.sleep(5)

# Get results
if status == "COMPLETED":
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/results")
    results = response.json()
    print(f"Results: {len(results['results'])} tasks")
```

---

## 📖 Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

These provide:
- Interactive API testing
- Request/response schemas
- Example values
- Authentication testing (when implemented)

---

## 🔍 Monitoring Endpoints

### Queue Metrics

Use AWS CloudWatch or query SQS directly:

```python
import boto3

sqs = boto3.client('sqs')
response = sqs.get_queue_attributes(
    QueueUrl='YOUR_QUEUE_URL',
    AttributeNames=[
        'ApproximateNumberOfMessages',
        'ApproximateNumberOfMessagesNotVisible',
        'ApproximateNumberOfMessagesDelayed'
    ]
)
print(response['Attributes'])
```

### Database Metrics

Query monitoring views:

```sql
-- Job progress
SELECT * FROM job_progress_summary 
WHERE status != 'COMPLETED' 
ORDER BY created_at DESC;

-- Failed jobs
SELECT * FROM failed_jobs_summary 
ORDER BY last_error_at DESC 
LIMIT 10;
```

---

## 📞 Support & Troubleshooting

For common issues, see the [SETUP_GUIDE.md](./SETUP_GUIDE.md) troubleshooting section.

For detailed implementation info, see [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md).

