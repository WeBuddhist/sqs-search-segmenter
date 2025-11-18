# AWS ECS Fargate - Quick Start

Ultra-fast deployment guide for experienced AWS users.

## Prerequisites

- ✅ AWS CLI configured (`aws configure`)
- ✅ Docker installed and running
- ✅ jq and envsubst installed
- ✅ All service credentials ready (Neo4j, Milvus, Firebase, Gemini)

## 3-Step Deployment

### Step 1: Create Infrastructure (~3 minutes)

```bash
cd /path/to/sqs-search-segmenter

# Create SQS queues
./setup_sqs.sh

# Create ECS cluster, ALB, ECR, IAM roles, security groups
./deploy/ecs-setup.sh
```

### Step 2: Store Secrets (~3 minutes)

```bash
# Store all credentials in AWS Secrets Manager
./deploy/secrets-setup.sh

# Follow prompts or load from existing .env file
```

### Step 3: Deploy Application (~10 minutes)

```bash
# Build, push to ECR, and deploy to ECS
./deploy/deploy.sh
```

## Access Your Application

After deployment completes, the script outputs your API URL:

```bash
# Test health
curl http://your-alb-dns.amazonaws.com/health

# Submit job
curl -X POST http://your-alb-dns.amazonaws.com/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"manifestation_id": "test-123"}'

# View API docs
open http://your-alb-dns.amazonaws.com/docs
```

## Monitor

```bash
# View worker logs
aws logs tail /ecs/sqs-search-segmenter-worker --follow

# View API logs
aws logs tail /ecs/sqs-search-segmenter-api --follow

# Check service status
aws ecs describe-services \
  --cluster sqs-search-segmenter-cluster \
  --services sqs-search-segmenter-api sqs-search-segmenter-worker
```

## Scale

```bash
# Scale workers (2 tasks = 8 workers, 4 tasks = 16 workers)
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-worker \
  --desired-count 4

# Scale API
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-api \
  --desired-count 2
```

## Update Deployment

```bash
# Make code changes, then:
./deploy/deploy.sh
```

## Troubleshooting

**Service won't start?**
```bash
aws ecs describe-services --cluster sqs-search-segmenter-cluster --services sqs-search-segmenter-api
aws logs tail /ecs/sqs-search-segmenter-api --follow
```

**Workers not processing?**
```bash
aws logs tail /ecs/sqs-search-segmenter-worker --follow
```

**Need to update a secret?**
```bash
aws secretsmanager update-secret \
  --secret-id sqs-search-segmenter/SECRET_NAME \
  --secret-string "NEW_VALUE"

# Then force redeployment
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-worker \
  --force-new-deployment
```

## Cost

**Minimal setup**: ~$100/month
- 1 API task (0.5 vCPU, 1GB): $15/month
- 2 Worker tasks (1 vCPU, 2GB each): $60/month
- Application Load Balancer: $20/month
- Other (ECR, logs, secrets): $5/month

## Full Documentation

See [README_DEPLOYMENT.md](../README_DEPLOYMENT.md) for complete documentation.

## Architecture

```
Internet → ALB → ECS API (1 task) → SQS → ECS Workers (2 tasks × 4 = 8 workers)
                                      ↓
                               Neo4j, Milvus, Firebase, Gemini
```

---

**Total Time**: 15-20 minutes from zero to deployed

