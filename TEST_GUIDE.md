# Testing Guide for SQS Multi-Worker System

## Quick Test (5 minutes)

### Step 1: Set Up AWS SQS Queues

```bash
# Run the setup script
./setup_sqs.sh

# Copy the output SQS_QUEUE_URL to your .env file
```

### Step 2: Configure Environment

Make sure your `.env` file has all required variables:

```bash
# Check if .env exists
ls -la .env

# Essential variables needed:
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/account/queue-name

NEO4J_URI=bolt://your-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

MILVUS_URI=your-milvus-uri
MILVUS_TOKEN=your-token
MILVUS_COLLECTION_NAME=your-collection

GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
FIREBASE_STORAGE_BUCKET=your-bucket

GEMINI_API_KEY=your-api-key
```

### Step 3: Start Services

#### Option A: Docker (Recommended)

```bash
# Start all services in background
docker-compose up -d

# Check services are running
docker-compose ps

# Expected output:
# NAME                STATUS              PORTS
# web                 Up                  0.0.0.0:8080->8080/tcp
# worker              Up
```

#### Option B: Local Development

```bash
# Terminal 1: Start API
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Start Workers
source venv/bin/activate
python -m app.worker
```

### Step 4: Test API Health

```bash
# Test API is responding
curl http://localhost:8080/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "api",
#   "note": "Workers run separately - check worker logs for processing status"
# }

# Test root endpoint
curl http://localhost:8080/

# Check API documentation
open http://localhost:8080/docs  # Opens Swagger UI
```

### Step 5: Submit a Test Job

```bash
# Submit a job with a test manifestation_id
curl -X POST http://localhost:8080/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "I1PD95844"}'

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "manifestation_id": "I1PD95844",
#   "message": "Job enqueued successfully. MessageId: abc123..."
# }

# Save the job_id for tracking in logs
```

### Step 6: Monitor Worker Logs

#### Docker

```bash
# Watch all worker logs (real-time)
docker-compose logs -f worker

# Look for patterns like:
# [Worker-1] Starting processing for manifestation I1PD95844
# [Worker-1] Manifestation id: I1PD95844 has Expression id: ...
# [Worker-1] Language: bo, Title: ...
# [Worker-1] Retrieved base text with 5000 characters
# [Worker-1] Fetched 50 search segments from Neo4j
# [Worker-1] Processed 50 segments with content
# [Worker-1] ✅ Successfully completed processing for manifestation I1PD95844

# Filter for specific job_id
docker-compose logs worker | grep "550e8400-e29b-41d4-a716-446655440000"

# Filter for errors only
docker-compose logs worker | grep "❌ FAILED"
```

#### Local

```bash
# Check the terminal where you ran python -m app.worker
# You'll see logs from all 4 workers in real-time
```

### Step 7: Check SQS Queue Status

```bash
# Check main queue
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible,ApproximateNumberOfMessagesDelayed \
  --region $AWS_REGION

# Key metrics:
# - ApproximateNumberOfMessages: Waiting to be processed
# - ApproximateNumberOfMessagesNotVisible: Currently being processed
# - ApproximateNumberOfMessagesDelayed: Delayed messages

# Check Dead Letter Queue
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages \
  --region $AWS_REGION

# If any messages in DLQ, they failed after 5 retries
```

## Advanced Testing

### Test 1: Submit Multiple Jobs

```bash
# Submit 10 jobs to test parallel processing
for i in {1..10}; do
  curl -X POST http://localhost:8080/jobs/create \
    -H "Content-Type: application/json" \
    -d "{\"manifestation_id\": \"test-$i\"}" &
done
wait

# Watch worker logs - you should see all 4 workers picking up jobs
docker-compose logs -f worker
```

### Test 2: Test Worker Failure & Retry

```bash
# Temporarily stop Neo4j or use invalid manifestation_id
curl -X POST http://localhost:8080/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "INVALID_ID_12345"}'

# Watch worker logs - you'll see:
# [Worker-1] Starting processing for manifestation INVALID_ID_12345
# [Worker-1] ❌ FAILED processing manifestation INVALID_ID_12345: Error message

# Message will retry up to 5 times, then move to DLQ
# Check DLQ after ~15 minutes (5 retries × visibility timeout)
```

### Test 3: Test Worker Restart

```bash
# Restart workers while jobs are processing
docker-compose restart worker

# Workers should:
# 1. Gracefully shutdown
# 2. In-progress messages return to queue after visibility timeout
# 3. New workers pick them up
# 4. Jobs complete successfully
```

### Test 4: Scale Workers

```bash
# Edit app/worker.py and change:
num_workers = 8  # Change from 4 to 8

# Restart workers
docker-compose restart worker

# Submit jobs and watch 8 workers process them
docker-compose logs -f worker | grep "Worker-"
```

### Test 5: Test API Under Load

```bash
# Install apache bench (if not installed)
# brew install apache2  # macOS
# sudo apt install apache2-utils  # Linux

# Send 100 requests with 10 concurrent connections
ab -n 100 -c 10 -p payload.json -T application/json \
  http://localhost:8080/jobs/create

# Where payload.json contains:
# {"manifestation_id": "I1PD95844"}

# Check all jobs are enqueued successfully
```

## Monitoring Commands

### View Service Status

```bash
# Docker
docker-compose ps
docker-compose stats  # Resource usage

# Check API logs
docker-compose logs -f web

# Check worker logs
docker-compose logs -f worker

# Check specific worker errors
docker-compose logs worker 2>&1 | grep -i error
```

### SQS Queue Monitoring

```bash
# Create monitoring script
cat > monitor_sqs.sh << 'EOF'
#!/bin/bash
QUEUE_URL=$1
REGION=${AWS_REGION:-us-east-1}

while true; do
  clear
  echo "=== SQS Queue Monitor ==="
  echo "Queue: $QUEUE_URL"
  echo "Time: $(date)"
  echo
  
  aws sqs get-queue-attributes \
    --queue-url "$QUEUE_URL" \
    --attribute-names All \
    --region "$REGION" \
    --output table
  
  sleep 5
done
EOF

chmod +x monitor_sqs.sh

# Run monitor
./monitor_sqs.sh $SQS_QUEUE_URL
```

### Worker Performance

```bash
# Count successful jobs in last hour
docker-compose logs --since 1h worker | grep -c "✅ Successfully completed"

# Count failed jobs in last hour
docker-compose logs --since 1h worker | grep -c "❌ FAILED"

# Average processing time (if you log timestamps)
docker-compose logs worker | grep "Retrieved base text" | tail -20
```

## Troubleshooting Tests

### Test: Workers Not Picking Up Jobs

```bash
# 1. Check workers are running
docker-compose ps

# 2. Check worker logs for startup errors
docker-compose logs worker | head -50

# 3. Check SQS queue has messages
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages

# 4. Check AWS credentials
aws sts get-caller-identity

# 5. Test SQS connectivity
aws sqs receive-message \
  --queue-url $SQS_QUEUE_URL \
  --max-number-of-messages 1 \
  --region $AWS_REGION
```

### Test: Jobs Failing

```bash
# 1. Check full error in worker logs
docker-compose logs worker | grep -A 20 "FAILED"

# 2. Check Neo4j connection
docker-compose exec worker python -c "
from app.neo4j_database import Neo4JDatabase
db = Neo4JDatabase()
print('Neo4j connected successfully')
"

# 3. Check Firebase connection
docker-compose exec worker python -c "
from app.storage import Storage
storage = Storage()
print('Firebase connected successfully')
"

# 4. Check Milvus connection
docker-compose exec worker python -c "
from app.config import get
print(f'Milvus URI: {get(\"MILVUS_URI\")}')
"
```

## Success Criteria

Your system is working correctly if:

- ✅ API responds to health check
- ✅ Jobs are enqueued successfully (receive job_id)
- ✅ Worker logs show job processing starts
- ✅ Worker logs show successful completion (✅)
- ✅ No messages in Dead Letter Queue (or expected failures only)
- ✅ SQS queue empties after processing
- ✅ All 4 workers are active and processing jobs

## Common Issues & Solutions

### Issue: "SQS_QUEUE_URL not configured"

```bash
# Solution: Run setup script and add to .env
./setup_sqs.sh
echo "SQS_QUEUE_URL=your-queue-url" >> .env
docker-compose restart
```

### Issue: "AWS credentials not found"

```bash
# Solution: Configure AWS CLI
aws configure
# Or add to .env:
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Issue: "Neo4j connection failed"

```bash
# Solution: Check Neo4j is running and credentials are correct
echo "NEO4J_URI=bolt://your-neo4j:7687" >> .env
echo "NEO4J_USER=neo4j" >> .env
echo "NEO4J_PASSWORD=your-password" >> .env
docker-compose restart worker
```

### Issue: Workers not starting

```bash
# Check logs for startup errors
docker-compose logs worker

# Rebuild containers
docker-compose build worker
docker-compose up -d worker
```

## Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (if needed)
docker-compose down -v

# Delete SQS queues (if testing complete)
aws sqs delete-queue --queue-url $SQS_QUEUE_URL
aws sqs delete-queue --queue-url $DLQ_URL
```

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Test with real manifestation IDs from your system
3. ✅ Load test with expected traffic volume
4. ✅ Set up monitoring alerts
5. ✅ Deploy to production
6. ✅ Monitor production logs for first few days

---

**Happy Testing!** 🧪

For issues, check:
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [docs/SQS_SETUP.md](docs/SQS_SETUP.md)
- Worker logs: `docker-compose logs -f worker`

