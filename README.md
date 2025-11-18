# SQS Search Segmenter

Fire-and-forget background job processing service for OpenPecha segment analysis using AWS SQS with 4 parallel workers.

## 🚀 Quick Start

```bash
# 1. Set up AWS SQS queues
./setup_sqs.sh

# 2. Configure environment
cp .env.example .env  # Edit with your credentials

# 3. Deploy with Docker
docker-compose up -d

# 4. Test the system
curl -X POST http://localhost:8080/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "test-id"}'
```

📘 See [DEPLOYMENT.md](DEPLOYMENT.md) for local Docker setup  
☁️ See [README_DEPLOYMENT.md](README_DEPLOYMENT.md) for **AWS ECS Fargate deployment** (production)

## Architecture

```
External Server → API (Port 8080) → AWS SQS Queue → 4 Workers → Process Jobs
                                          ↓
                                   Dead Letter Queue
                                    (failed jobs)
```

### Components

- **API Service**: FastAPI REST API for submitting jobs
- **Worker Service**: 4 parallel processes polling SQS and processing jobs  
- **AWS SQS**: Message queue with automatic retries (5 attempts) and DLQ
- **Neo4j**: Graph database for segments
- **Firebase**: Storage for base texts
- **Milvus**: Vector database for processed segments

## System Flow

1. External server calls `POST /jobs/create` with `manifestation_id`
2. API generates `job_id` and enqueues message to SQS
3. One of 4 workers picks up the message
4. Worker processes job:
   - Fetches data from Neo4j
   - Retrieves base text from Firebase
   - Processes segments
   - Uploads to Milvus vector database
   - Logs success/failure
5. On success: Message deleted from queue
6. On failure: Message retries (max 5 times) then moves to DLQ

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- AWS account with SQS access
- Neo4j database
- Milvus vector database
- Firebase Storage
- Gemini API key

## Configuration

Create `.env` file:

```bash
# AWS SQS (Required)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/account/queue-name

# Neo4j (Required)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Milvus (Required)
MILVUS_URI=your-milvus-uri
MILVUS_TOKEN=your-token
MILVUS_COLLECTION_NAME=your-collection

# Firebase (Required)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
FIREBASE_STORAGE_BUCKET=your-bucket

# API Keys (Required)
GEMINI_API_KEY=your-gemini-api-key

# Optional
LOG_LEVEL=INFO
```

## Deployment Options

### Option 1: AWS ECS Fargate (Production - Fully Managed)

For production deployment with fully managed infrastructure:

```bash
# See complete guide in README_DEPLOYMENT.md
./deploy/ecs-setup.sh      # Create infrastructure
./deploy/secrets-setup.sh  # Store secrets
./deploy/deploy.sh         # Deploy application
```

**Benefits**:
- ✅ Fully managed (no server maintenance)
- ✅ Auto-scaling capabilities
- ✅ High availability with ALB
- ✅ Secure credential management (AWS Secrets Manager)
- ✅ Centralized logging (CloudWatch)
- ✅ ~$100/month for minimal setup

📘 **Full guide**: [README_DEPLOYMENT.md](README_DEPLOYMENT.md)  
⚡ **Quick start**: [deploy/QUICK_START.md](deploy/QUICK_START.md)

### Option 2: Docker Compose (Local/Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web      # API logs
docker-compose logs -f worker   # Worker logs

# Stop services
docker-compose down
```

### Local Development

```bash
# Terminal 1: Start API
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Start Workers (4 processes)
python -m app.worker
```

## API Endpoints

### Submit Job (Fire-and-Forget)

```bash
POST /jobs/create
Content-Type: application/json

{
  "manifestation_id": "M001"
}
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "M001",
  "message": "Job enqueued successfully. MessageId: abc123..."
}
```

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "api",
  "note": "Workers run separately - check worker logs for processing status"
}
```

### API Documentation

Interactive API docs available at: `http://localhost:8080/docs`

## Monitoring

### Worker Logs

```bash
# Docker
docker-compose logs -f worker

# Look for patterns:
# [Worker-1] Starting processing for manifestation abc123
# [Worker-1] ✅ Successfully completed processing for manifestation abc123
# [Worker-1] ❌ FAILED processing manifestation abc123: Error message
```

### SQS Queue Monitoring

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

## Scaling

### Increase Worker Count

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

## Project Structure

```
sqs-search-segmenter/
├── app/
│   ├── api/
│   │   └── enqueue.py          # Job submission API
│   ├── worker.py               # Multi-process SQS worker ⭐ NEW
│   ├── main.py                 # FastAPI app (API only)
│   ├── tasks.py                # Core processing logic
│   ├── sqs_service.py          # SQS consumer class
│   ├── neo4j_database.py       # Neo4j operations
│   ├── storage.py              # Firebase storage
│   ├── segmentation.py         # Segmentation logic
│   └── config.py               # Configuration
├── docs/
│   └── SQS_SETUP.md            # Detailed setup guide
├── setup_sqs.sh                # AWS SQS setup script ⭐ NEW
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Container definition
├── DEPLOYMENT.md               # Quick deployment guide ⭐ NEW
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## Key Features

- ✅ **Fire-and-Forget**: Submit jobs without tracking status
- ✅ **Parallel Processing**: 4 workers process jobs simultaneously
- ✅ **Automatic Retries**: Failed jobs retry up to 5 times
- ✅ **Dead Letter Queue**: Persistent failures go to DLQ for review
- ✅ **Long Polling**: Efficient SQS polling (reduces costs)
- ✅ **Comprehensive Logging**: Track all job processing
- ✅ **Easy Scaling**: Add more workers with simple config change
- ✅ **Docker Ready**: One-command deployment

## Troubleshooting

### Workers Not Processing Messages

```bash
# Check workers are running
docker-compose ps

# Check worker logs
docker-compose logs worker | grep ERROR

# Restart workers
docker-compose restart worker
```

### Jobs Failing Repeatedly

```bash
# View error logs
docker-compose logs worker | grep "FAILED"

# Check dead letter queue
aws sqs receive-message \
  --queue-url $DLQ_URL \
  --max-number-of-messages 1 \
  --region us-east-1
```

### Common Issues

1. **No AWS credentials**: Run `aws configure`
2. **Wrong queue URL**: Check `SQS_QUEUE_URL` in `.env`
3. **Neo4j connection failed**: Verify `NEO4J_URI` and credentials
4. **Firebase auth failed**: Check `GOOGLE_APPLICATION_CREDENTIALS` path
5. **Slow processing**: Increase worker count or check network latency

## Documentation

- **[Quick Deployment](DEPLOYMENT.md)** - Get started in 5 minutes
- **[Detailed SQS Setup](docs/SQS_SETUP.md)** - Comprehensive guide with monitoring
- **[API Docs](http://localhost:8080/docs)** - Interactive API documentation

## SQS Configuration

### Queue Settings

- **Visibility Timeout**: 900 seconds (15 minutes)
- **Message Retention**: 4 days
- **Max Retries**: 5 attempts before DLQ
- **Long Polling**: 20 seconds
- **DLQ**: Captures permanently failed jobs

### How Retries Work

1. Worker picks up message (invisible for 15 min)
2. If processing fails, message returns to queue after timeout
3. Another worker can pick it up
4. After 5 failed attempts, message moves to DLQ
5. DLQ messages require manual investigation

## Production Checklist

- [ ] AWS SQS queues created (main + DLQ)
- [ ] IAM permissions configured
- [ ] Environment variables set
- [ ] Workers deployed and running
- [ ] Monitoring/alerting for DLQ
- [ ] Logs aggregated (CloudWatch/ELK)
- [ ] Load testing completed
- [ ] Auto-scaling configured (if needed)

## Support

Need help?

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for setup issues
2. Check [docs/SQS_SETUP.md](docs/SQS_SETUP.md) for detailed configuration
3. Review worker logs: `docker-compose logs -f worker`
4. Check SQS metrics in AWS Console
5. Contact the development team

## License

[Your License]

---

**Status**: Production Ready ✅  
**Last Updated**: 2025-11-18  
**Version**: 2.0.0 (Multi-Worker SQS)

