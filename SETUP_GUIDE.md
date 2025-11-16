# 🚀 Setup Guide - SQS Search Segmenter

This guide will walk you through setting up and deploying the SQS-based background job system.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.9+** installed
- **PostgreSQL** database running
- **Neo4j** database running
- **AWS Account** with SQS access
- **Docker** (optional, for containerized deployment)
- **Firebase/GCS** credentials (for storage)

---

## ⚙️ Step 1: Environment Setup

1. **Clone the repository** (or navigate to your project directory)

```bash
cd sqs-search-segmenter
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Create environment file**

Copy `env.example` to `.env` and fill in your actual values:

```bash
cp env.example .env
```

Edit `.env` with your credentials:

```bash
# PostgreSQL
POSTGRES_URL=postgresql://admin:password@localhost:5432/pecha

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# AWS SQS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123/queue.fifo

# Optional: Firebase
GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccount.json
```

---

## 🗄️ Step 2: Database Setup

### PostgreSQL

1. **Initialize the database schema**

Using Python script (recommended):
```bash
python init_db.py init
```

Or using SQL directly:
```bash
psql -U admin -d pecha -f db_schema.sql
```

2. **Verify tables were created**

```bash
python init_db.py info
```

You should see `root_jobs` and `manifestation_tasks` tables.

### Neo4j

Ensure your Neo4j database is running and contains the required graph data:
- Expression nodes
- Manifestation nodes
- Segment nodes
- Annotation nodes with relationships

---

## ☁️ Step 3: AWS SQS Setup

### Create SQS Queue

1. **Go to AWS Console** → SQS

2. **Create a FIFO Queue**
   - Name: `segmentation-queue.fifo`
   - Enable **Content-based deduplication**: Yes
   - **Visibility timeout**: 300 seconds (5 minutes)
   - **Message retention**: 4 days
   - **Receive message wait time**: 20 seconds (long polling)

3. **Create Dead Letter Queue (DLQ)**
   - Name: `segmentation-queue-dlq.fifo`
   - Configure main queue to use DLQ after 3 receive attempts

4. **Copy Queue URL** and add to `.env` file

### IAM Permissions

Ensure your IAM user/role has these permissions:

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
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:REGION:ACCOUNT:segmentation-queue.fifo"
    }
  ]
}
```

---

## 🏃 Step 4: Running the Application

### Local Development

**Start the FastAPI server:**

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

The application will:
- Start the API server on port 8080
- Automatically start the SQS consumer in a background thread
- Begin polling SQS for messages

**Access the API:**
- API Docs: http://localhost:8080/docs
- Health Check: http://localhost:8080/health
- Root Info: http://localhost:8080/

### Using Docker

**Build the Docker image:**

```bash
docker build -t sqs-search-segmenter .
```

**Run with docker-compose:**

```bash
docker-compose up -d
```

This will start the service in the background.

**View logs:**

```bash
docker-compose logs -f web
```

---

## 🧪 Step 5: Testing the System

### 1. Create a Job

```bash
curl -X POST "http://localhost:8080/jobs/create" \
  -H "Content-Type: application/json" \
  -d '{
    "manifestation_id": "test-manifestation-001"
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "manifestation_id": "test-manifestation-001",
  "total_segments": 10,
  "status": "QUEUED",
  "message": "Job created and enqueued successfully"
}
```

### 2. Check Job Status

```bash
curl "http://localhost:8080/jobs/{job_id}/status"
```

### 3. Get Results (when completed)

```bash
curl "http://localhost:8080/jobs/{job_id}/results"
```

Or by manifestation ID:

```bash
curl "http://localhost:8080/segmentation/{manifestation_id}/segments"
```

---

## 📊 Step 6: Monitoring

### Check SQS Consumer Status

```bash
curl http://localhost:8080/health
```

### Monitor Queue Metrics

In AWS Console:
- **ApproximateNumberOfMessages**: Messages waiting to be processed
- **ApproximateNumberOfMessagesNotVisible**: Messages being processed
- **NumberOfMessagesDeleted**: Successfully processed messages
- **ApproximateAgeOfOldestMessage**: How long oldest message has been in queue

### Database Monitoring

Check job progress:
```sql
SELECT * FROM job_progress_summary;
```

Check failed jobs:
```sql
SELECT * FROM failed_jobs_summary;
```

---

## 🔧 Step 7: Configuration & Tuning

### SQS Consumer Settings

In `app/sqs_service.py`:

```python
consumer = SegmentationConsumer(
    queue_url=queue_url,
    region=get("AWS_REGION"),
    polling_wait_time_ms=20000,      # Long polling duration
    visibility_timeout_ms=300000,    # 5 minutes - adjust based on job duration
    aws_access_key_id=get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=get("AWS_SECRET_ACCESS_KEY")
)
```

### Database Connection Pool

In `app/db/postgres.py`:

```python
engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
    pool_size=10,          # Adjust based on concurrency needs
    max_overflow=20,       # Additional connections if pool exhausted
    echo=False
)
```

---

## 🚨 Troubleshooting

### Issue: Jobs stay in QUEUED status

**Possible causes:**
1. SQS consumer not running
2. Wrong queue URL
3. AWS credentials invalid

**Solutions:**
- Check `/health` endpoint
- Verify `.env` configuration
- Check logs for errors

### Issue: Jobs fail repeatedly

**Possible causes:**
1. Neo4j connection issues
2. Storage/Firebase credentials incorrect
3. Data not found in Neo4j or storage

**Solutions:**
- Check error messages in database: `SELECT * FROM failed_jobs_summary`
- Test Neo4j connectivity
- Verify storage credentials

### Issue: Slow processing

**Possible causes:**
1. Database connection pool too small
2. Visibility timeout too short
3. Neo4j queries not optimized

**Solutions:**
- Increase pool size in postgres.py
- Increase visibility timeout in SQS
- Add indexes to Neo4j queries

---

## 📦 Deployment Options

### Option 1: AWS ECS/Fargate

1. Push Docker image to ECR
2. Create ECS task definition
3. Create ECS service with desired count
4. Configure auto-scaling based on SQS queue length

### Option 2: AWS EC2

1. Launch EC2 instance
2. Install dependencies
3. Use systemd service for automatic restart
4. Setup CloudWatch for monitoring

### Option 3: Kubernetes

1. Create deployment YAML
2. Configure ConfigMap for environment variables
3. Setup HorizontalPodAutoscaler based on queue metrics
4. Deploy using kubectl

---

## 📝 API Endpoints

### Job Management (`/jobs`)

- `POST /jobs/create` - Create and enqueue a new job
- `GET /jobs/{job_id}/status` - Get job status and progress
- `GET /jobs/{job_id}/results` - Get completed job results

### Segmentation Results (`/segmentation`)

- `GET /segmentation/{manifestation_id}/segments` - Get processed segments
- `GET /segmentation/{manifestation_id}/neo4j-segments` - Get raw Neo4j data

### System

- `GET /` - Service information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

---

## 🎯 Next Steps

1. **Production Checklist:**
   - [ ] Setup CloudWatch logging
   - [ ] Configure DLQ alerts
   - [ ] Add Sentry/error tracking
   - [ ] Setup database backups
   - [ ] Configure SSL/TLS
   - [ ] Add authentication/authorization
   - [ ] Setup CI/CD pipeline

2. **Optimization:**
   - [ ] Add caching layer (Redis)
   - [ ] Implement batch processing
   - [ ] Add result pagination
   - [ ] Optimize Neo4j queries
   - [ ] Add compression for large results

3. **Monitoring:**
   - [ ] Setup Grafana dashboards
   - [ ] Configure Prometheus metrics
   - [ ] Add custom CloudWatch metrics
   - [ ] Setup alerting rules

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f` or application logs
- Review database: `SELECT * FROM failed_jobs_summary`
- Check SQS DLQ for failed messages
- Review Neo4j connectivity

---

**Congratulations!** 🎉 Your SQS-based background job system is now fully functional!

