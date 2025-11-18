# Quick Deployment Guide

This is a condensed guide for quickly deploying the SQS segmentation worker system.

## Quick Start (5 minutes)

### 1. Set Up AWS SQS

```bash
# Run the setup script
./setup_sqs.sh

# Copy the output SQS_QUEUE_URL to your .env file
```

### 2. Configure Environment

Create `.env` file:

```bash
# Copy from template
cp .env.example .env  # If you have a template

# Or create manually with these required variables:
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
SQS_QUEUE_URL=your-queue-url-from-step-1
NEO4J_URI=bolt://your-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
MILVUS_URI=your-milvus-uri
MILVUS_TOKEN=your-token
MILVUS_COLLECTION_NAME=your-collection
FIREBASE_STORAGE_BUCKET=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GEMINI_API_KEY=your-api-key
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Test the System

```bash
# Test API health
curl http://localhost:8080/health

# Submit a test job
curl -X POST http://localhost:8080/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "test-id-123"}'

# Watch worker logs
docker-compose logs -f worker
```

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│ External Server │────────>│  Web API     │────────>│   AWS SQS       │
│                 │         │ (Port 8080)  │         │  Main Queue     │
└─────────────────┘         └──────────────┘         └────────┬────────┘
                                                               │
                                                               v
                            ┌──────────────────────────────────────────┐
                            │          Worker Service                  │
                            │  ┌─────────┐  ┌─────────┐               │
                            │  │Worker 1 │  │Worker 2 │               │
                            │  └─────────┘  └─────────┘               │
                            │  ┌─────────┐  ┌─────────┐               │
                            │  │Worker 3 │  │Worker 4 │               │
                            │  └─────────┘  └─────────┘               │
                            └──────────────────────────────────────────┘
                                           │
                                           v
                            ┌──────────────────────────────┐
                            │    Processing Pipeline       │
                            │  Neo4j → Firebase → Milvus   │
                            └──────────────────────────────┘
```

## Services

### Web Service (API)
- **Port**: 8080
- **Purpose**: Accepts job requests, enqueues to SQS
- **Endpoints**:
  - `GET /` - Service info
  - `GET /health` - Health check
  - `POST /jobs/create` - Submit new job
  - `GET /docs` - API documentation

### Worker Service
- **Processes**: 4 parallel workers
- **Purpose**: Polls SQS and processes jobs
- **No exposed ports** (internal service)

## Monitoring

### Check Service Status

```bash
# All services
docker-compose ps

# Web logs
docker-compose logs -f web

# Worker logs
docker-compose logs -f worker
```

### Monitor SQS Queue

```bash
# Main queue stats
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible \
  --region us-east-1

# Dead letter queue (failed jobs)
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

### Check Worker Performance

Worker logs show:
```
[Worker-1] Starting processing for manifestation abc123
[Worker-1] Retrieved base text with 5000 characters
[Worker-1] Fetched 50 search segments from Neo4j
[Worker-1] ✅ Successfully completed processing for manifestation abc123
```

## Scaling

### Increase Workers

Edit `app/worker.py`:
```python
num_workers = 8  # Change from 4 to 8
```

Then restart:
```bash
docker-compose restart worker
```

### Multiple Worker Containers

Edit `docker-compose.yml`:
```yaml
worker:
  deploy:
    replicas: 2  # 2 containers × 4 workers = 8 total
```

## Troubleshooting

### Workers Not Processing

```bash
# Check if workers are running
docker-compose ps

# Check worker logs for errors
docker-compose logs worker | grep ERROR

# Restart workers
docker-compose restart worker
```

### Jobs Failing

```bash
# Check error logs
docker-compose logs worker | grep "FAILED"

# Check dead letter queue
aws sqs receive-message \
  --queue-url $DLQ_URL \
  --region us-east-1
```

### High Latency

- Increase worker count
- Check Neo4j/Firebase/Milvus connection speeds
- Adjust visibility timeout if jobs take >15 minutes

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Production Deployment

For production environments:

1. **Use managed services**:
   - AWS ECS/Fargate for containers
   - AWS SQS (already using)
   - Managed Neo4j/Milvus

2. **Set up monitoring**:
   - CloudWatch for logs and metrics
   - SQS alarms for DLQ messages
   - Worker health checks

3. **Configure auto-scaling**:
   - Scale workers based on queue depth
   - Set min/max worker counts

4. **Secure credentials**:
   - Use AWS Secrets Manager
   - IAM roles instead of access keys
   - Rotate credentials regularly

5. **Backup & DR**:
   - Document recovery procedures
   - Test failover scenarios
   - Monitor SQS DLQ

For detailed information, see [SQS_SETUP.md](docs/SQS_SETUP.md).

---

**System Status**: Production Ready ✅
**Last Updated**: 2025-11-18

