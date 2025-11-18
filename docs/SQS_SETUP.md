# AWS SQS Multi-Worker Setup Guide

This guide explains how to set up and run the SQS-based segmentation worker system with 4 parallel workers.

## Architecture Overview

The system consists of two main components:

1. **Web Service (API)**: FastAPI application that accepts job requests and enqueues them to SQS
2. **Worker Service**: 4 parallel worker processes that poll SQS and process jobs

```
External Server → API (POST /jobs/create) → AWS SQS Queue → 4 Workers → Process Jobs
                                                  ↓
                                            Dead Letter Queue (failed jobs)
```

## Prerequisites

1. **AWS Account** with SQS access
2. **AWS CLI** installed and configured
3. **Python 3.12+**
4. **Docker & Docker Compose** (for containerized deployment)
5. **Environment variables** configured (see below)

## Step 1: AWS SQS Configuration

### Option A: Automated Setup (Recommended)

Run the provided setup script:

```bash
./setup_sqs.sh
```

This script will:
- Create a Dead Letter Queue (DLQ) for failed messages
- Create the main processing queue
- Configure retry policy (5 retries before moving to DLQ)
- Set visibility timeout to 900 seconds (15 minutes)
- Enable long polling (20 seconds)

### Option B: Manual Setup

#### 1. Create Dead Letter Queue

```bash
aws sqs create-queue \
    --queue-name segmentation-dlq \
    --region us-east-1 \
    --attributes '{
        "MessageRetentionPeriod": "345600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }'
```

#### 2. Get DLQ ARN

```bash
DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url <DLQ_URL> \
    --region us-east-1 \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)
```

#### 3. Create Main Queue with Redrive Policy

```bash
aws sqs create-queue \
    --queue-name segmentation-processing-queue \
    --region us-east-1 \
    --attributes '{
        "VisibilityTimeout": "900",
        "MessageRetentionPeriod": "345600",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":5}"
    }'
```

## Step 2: Environment Configuration

Create a `.env` file in the project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/segmentation-processing-queue

# Neo4j Configuration
NEO4J_URI=bolt://your-neo4j-host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Milvus Configuration
MILVUS_URI=your-milvus-uri
MILVUS_TOKEN=your-milvus-token
MILVUS_COLLECTION_NAME=your-collection-name

# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
FIREBASE_STORAGE_BUCKET=your-bucket-name

# API Keys
GEMINI_API_KEY=your-gemini-api-key

# Optional
LOG_LEVEL=INFO
```

## Step 3: IAM Permissions

Ensure your AWS IAM user/role has these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": [
        "arn:aws:sqs:us-east-1:123456789012:segmentation-processing-queue",
        "arn:aws:sqs:us-east-1:123456789012:segmentation-dlq"
      ]
    }
  ]
}
```

## Step 4: Running the System

### Option A: Docker Compose (Recommended for Production)

```bash
# Start both web service and workers
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f worker

# Stop services
docker-compose down
```

### Option B: Local Development

#### Terminal 1: Start Web Service (API)

```bash
# Activate virtual environment
source venv/bin/activate

# Start API
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

#### Terminal 2: Start Workers

```bash
# Activate virtual environment
source venv/bin/activate

# Start 4 worker processes
python -m app.worker
```

## Step 5: Testing the System

### 1. Check API Health

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "api",
  "note": "Workers run separately - check worker logs for processing status"
}
```

### 2. Submit a Test Job

```bash
curl -X POST http://localhost:8080/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "your-manifestation-id"}'
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "your-manifestation-id",
  "message": "Job enqueued successfully. MessageId: abc123..."
}
```

### 3. Monitor Worker Logs

```bash
# Docker
docker-compose logs -f worker

# Local
# Check the terminal where you ran python -m app.worker
```

Look for log messages like:
```
[Worker-1] Starting processing for manifestation your-manifestation-id
[Worker-1] Retrieved base text with 5432 characters
[Worker-1] Fetched 123 search segments from Neo4j
[Worker-1] ✅ Successfully completed processing for manifestation your-manifestation-id
```

### 4. Monitor SQS Queues

#### Check Main Queue

```bash
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names All \
  --region us-east-1
```

Key metrics:
- `ApproximateNumberOfMessages`: Messages waiting to be processed
- `ApproximateNumberOfMessagesNotVisible`: Messages currently being processed
- `ApproximateNumberOfMessagesDelayed`: Delayed messages

#### Check Dead Letter Queue

```bash
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names All \
  --region us-east-1
```

If messages appear in DLQ, they failed after 5 retry attempts and need investigation.

## How It Works

### Message Flow

1. **External server** calls `POST /jobs/create` with `manifestation_id`
2. **API** generates a `job_id` and sends message to SQS
3. **SQS** stores the message in the queue
4. **Workers** (1-4) poll SQS using long polling
5. **Worker** receives message and processes it:
   - Fetches data from Neo4j
   - Retrieves base text from Firebase
   - Processes segments
   - Uploads to Milvus vector database
   - Logs success/failure
6. On **success**: Message is deleted from queue
7. On **failure**: Message returns to queue (becomes visible after visibility timeout)
8. After **5 failed attempts**: Message moves to Dead Letter Queue

### Retry Logic

- **Visibility Timeout**: 900 seconds (15 minutes)
  - After a worker picks up a message, it's invisible to other workers for 15 minutes
  - If processing takes longer, the message may be reprocessed by another worker
  - Adjust if your jobs take longer than 15 minutes

- **Max Retries**: 5 attempts
  - If a job fails 5 times, it moves to the DLQ
  - Prevents infinite retry loops for permanently failing jobs

- **Long Polling**: 20 seconds
  - Workers wait up to 20 seconds for messages
  - Reduces API calls and improves efficiency

## Scaling

### Horizontal Scaling

To increase processing capacity, modify `app/worker.py`:

```python
num_workers = 8  # Change from 4 to 8
```

Or run multiple worker containers:

```yaml
# docker-compose.yml
worker:
  deploy:
    replicas: 2  # Runs 2 containers, each with 4 processes = 8 total workers
```

### Vertical Scaling

Increase resources for the worker container:

```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
```

## Monitoring & Troubleshooting

### Worker Health

Workers log their activity with structured messages:

```
[Worker-1] - Processing job 550e8400-e29b-41d4-a716-446655440000
[Worker-2] - ✅ Successfully completed job 660e8400-e29b-41d4-a716-446655440001
[Worker-3] - ❌ FAILED processing manifestation: ConnectionError
```

### Common Issues

#### 1. Messages Not Being Processed

**Check:**
- Are workers running? `docker-compose ps`
- Worker logs for errors: `docker-compose logs worker`
- SQS queue has messages: Check AWS Console or CLI

**Solution:**
- Restart workers: `docker-compose restart worker`
- Check AWS credentials are valid
- Verify SQS_QUEUE_URL is correct

#### 2. Jobs Failing Repeatedly

**Check:**
- Worker logs for error details
- Dead Letter Queue for failed messages

**Solution:**
- Review error messages in logs
- Verify Neo4j, Firebase, Milvus connections
- Check if manifestation_id exists in Neo4j

#### 3. Slow Processing

**Check:**
- How many workers are running?
- Network latency to AWS, Neo4j, Firebase, Milvus

**Solution:**
- Increase number of workers
- Run workers closer to your databases (same region/datacenter)
- Optimize visibility timeout

#### 4. Messages in DLQ

**Investigate:**
```bash
# Receive message from DLQ
aws sqs receive-message \
  --queue-url $DLQ_URL \
  --region us-east-1 \
  --max-number-of-messages 1
```

**Action:**
- Fix the underlying issue
- Manually reprocess by sending back to main queue
- Or delete if it's invalid data

## Performance Tuning

### Visibility Timeout

Adjust based on average job duration:

```bash
aws sqs set-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attributes '{"VisibilityTimeout":"1800"}'  # 30 minutes
```

Rule of thumb: Set to 2-3x your average processing time.

### Batch Size

Workers currently process one message at a time. For higher throughput, modify `app/worker.py` to process batches.

### Connection Pooling

The system uses connection pooling for Neo4j. Ensure pool size matches your worker count.

## Production Checklist

- [ ] AWS SQS queues created (main + DLQ)
- [ ] IAM permissions configured
- [ ] Environment variables set in `.env`
- [ ] Visibility timeout tuned for job duration
- [ ] Workers deployed and running
- [ ] Monitoring/alerting set up for DLQ
- [ ] Logs aggregated (CloudWatch, ELK, etc.)
- [ ] Load testing completed
- [ ] Auto-scaling configured (if using ECS/K8s)
- [ ] Backup/disaster recovery plan

## Cost Optimization

### SQS Costs

- **Requests**: $0.40 per million requests (first 1M free per month)
- **Long polling**: Reduces costs by reducing number of requests

### Worker Costs

- Run workers only when needed (scale down during low traffic)
- Use spot instances or preemptible VMs for cost savings
- Monitor idle workers and adjust count

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f worker`
2. Check SQS metrics in AWS Console
3. Review this documentation
4. Contact the development team

---

**Last Updated**: 2025-11-18

