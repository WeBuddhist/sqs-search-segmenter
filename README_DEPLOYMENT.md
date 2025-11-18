# AWS ECS Fargate Deployment Guide

Complete guide for deploying the SQS Search Segmenter application to AWS ECS Fargate.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [Post-Deployment](#post-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

## Overview

This deployment uses:

- **AWS ECS Fargate**: Serverless container orchestration
- **AWS ECR**: Private Docker image registry
- **Application Load Balancer**: API endpoint with health checks
- **AWS Secrets Manager**: Secure credential storage
- **CloudWatch Logs**: Centralized logging
- **IAM Roles**: Secure access without hardcoded credentials

### Architecture

```
Internet
   ↓
Application Load Balancer (Port 80)
   ↓
ECS Fargate - API Service (1 task)
   ↓
AWS SQS Queue
   ↓
ECS Fargate - Worker Service (2 tasks × 4 workers = 8 total)
   ↓
Neo4j, Milvus, Firebase, Gemini API
```

## Prerequisites

### Required Software

1. **AWS CLI** (v2.x or later)
   ```bash
   # Install on macOS
   brew install awscli
   
   # Configure
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (e.g., us-east-1)
   ```

2. **Docker** (v20.x or later)
   ```bash
   # Install Docker Desktop
   # https://www.docker.com/products/docker-desktop
   
   # Verify
   docker --version
   ```

3. **jq** (JSON processor)
   ```bash
   # Install on macOS
   brew install jq
   ```

4. **envsubst** (comes with gettext)
   ```bash
   # Install on macOS
   brew install gettext
   brew link --force gettext
   ```

### Required AWS Permissions

Your AWS IAM user/role needs permissions for:

- Amazon ECR (create repositories, push images)
- Amazon ECS (create clusters, services, task definitions)
- Application Load Balancer (create ALB, target groups, listeners)
- IAM (create roles, attach policies)
- AWS Secrets Manager (create secrets, get secret values)
- CloudWatch Logs (create log groups)
- EC2 (create security groups, describe VPCs/subnets)

### Required External Services

You must have credentials ready for:

- ✅ AWS SQS Queue (create with `./setup_sqs.sh`)
- ✅ Neo4j Database (URI, username, password)
- ✅ Milvus Vector Database (URI, token, collection name)
- ✅ Firebase Storage (service account JSON, bucket name)
- ✅ Gemini API (API key)

## Step-by-Step Deployment

### Step 1: Set Up AWS SQS Queue

If you haven't already created your SQS queue:

```bash
./setup_sqs.sh
```

This creates:
- Main processing queue
- Dead Letter Queue (DLQ) for failed messages

Copy the `SQS_QUEUE_URL` from the output.

### Step 2: Create AWS Infrastructure

Run the infrastructure setup script:

```bash
./deploy/ecs-setup.sh
```

This creates:
- ECR repositories for Docker images
- ECS cluster (Fargate)
- Application Load Balancer
- Target groups and listeners
- Security groups
- IAM roles with appropriate permissions
- CloudWatch log groups

**Duration**: ~2-3 minutes

**Output**: Configuration saved to `deploy/ecs-config.env`

### Step 3: Store Secrets in AWS Secrets Manager

Run the secrets setup script:

```bash
./deploy/secrets-setup.sh
```

This will:
1. Prompt for all credentials (or load from `.env` if available)
2. Securely store them in AWS Secrets Manager
3. Generate secret ARNs for ECS task definitions

**Required Information**:
- AWS Access Key ID & Secret Access Key
- SQS Queue URL (from Step 1)
- Neo4j credentials
- Milvus credentials
- Firebase service account JSON file path
- Gemini API key

**Duration**: ~2-3 minutes

**Output**: Secret ARNs saved to `deploy/secrets-arns.env`

### Step 4: Deploy Application

Run the deployment script:

```bash
./deploy/deploy.sh
```

This will:
1. Build Docker images for API and Worker
2. Tag and push images to ECR
3. Register ECS task definitions
4. Create or update ECS services
5. Wait for deployment to stabilize

**Duration**: ~10-15 minutes (first time), ~5-8 minutes (updates)

**Output**: Your API URL (ALB DNS name)

## Post-Deployment

### Verify Deployment

1. **Check API Health**:
   ```bash
   # Replace with your actual ALB DNS
   curl http://your-alb-dns-name.amazonaws.com/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "api"
   }
   ```

2. **Submit Test Job**:
   ```bash
   curl -X POST http://your-alb-dns-name.amazonaws.com/jobs/create \
     -H "Content-Type: application/json" \
     -d '{"manifestation_id": "test-123"}'
   ```

   Expected response:
   ```json
   {
     "job_id": "550e8400-...",
     "manifestation_id": "test-123",
     "message": "Job enqueued successfully. MessageId: ..."
   }
   ```

3. **Check Worker Logs**:
   ```bash
   aws logs tail /ecs/sqs-search-segmenter-worker --follow --region us-east-1
   ```

   Look for:
   ```
   [Worker-1] Starting processing for manifestation test-123
   [Worker-1] ✅ Successfully completed processing for manifestation test-123
   ```

### Access API Documentation

Visit the interactive API docs:
```
http://your-alb-dns-name.amazonaws.com/docs
```

## Monitoring & Maintenance

### View Logs

**API Logs**:
```bash
aws logs tail /ecs/sqs-search-segmenter-api --follow --region us-east-1
```

**Worker Logs**:
```bash
aws logs tail /ecs/sqs-search-segmenter-worker --follow --region us-east-1
```

**Filter for Errors**:
```bash
aws logs filter-log-events \
  --log-group-name /ecs/sqs-search-segmenter-worker \
  --filter-pattern "ERROR" \
  --region us-east-1
```

### Monitor Services

**Check Service Status**:
```bash
aws ecs describe-services \
  --cluster sqs-search-segmenter-cluster \
  --services sqs-search-segmenter-api sqs-search-segmenter-worker \
  --region us-east-1
```

**Check Running Tasks**:
```bash
aws ecs list-tasks \
  --cluster sqs-search-segmenter-cluster \
  --region us-east-1
```

### Monitor SQS Queue

**Queue Statistics**:
```bash
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names All \
  --region us-east-1
```

**Check Dead Letter Queue**:
```bash
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

### CloudWatch Metrics

View in AWS Console:
1. Go to CloudWatch → Metrics → ECS
2. Select your cluster: `sqs-search-segmenter-cluster`
3. Monitor:
   - CPUUtilization
   - MemoryUtilization
   - TaskCount

## Scaling

### Scale API Service

Increase API capacity for more concurrent requests:

```bash
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-api \
  --desired-count 2 \
  --region us-east-1
```

### Scale Worker Service

Increase worker capacity for faster job processing:

```bash
# 4 tasks = 16 parallel workers (4 workers per task)
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-worker \
  --desired-count 4 \
  --region us-east-1
```

**Worker Scaling Guide**:
- 1 task = 4 parallel workers
- 2 tasks = 8 parallel workers (default)
- 4 tasks = 16 parallel workers
- 8 tasks = 32 parallel workers

### Auto-Scaling (Optional)

Set up auto-scaling based on SQS queue depth:

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/sqs-search-segmenter-cluster/sqs-search-segmenter-worker \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 8 \
  --region us-east-1

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name worker-scale-on-queue-depth \
  --service-namespace ecs \
  --resource-id service/sqs-search-segmenter-cluster/sqs-search-segmenter-worker \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json \
  --region us-east-1
```

## Troubleshooting

### Service Won't Start

**Check Task Logs**:
```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster sqs-search-segmenter-cluster \
  --service-name sqs-search-segmenter-api \
  --region us-east-1 \
  --query 'taskArns[0]' \
  --output text)

# Check logs
aws ecs describe-tasks \
  --cluster sqs-search-segmenter-cluster \
  --tasks $TASK_ARN \
  --region us-east-1
```

**Common Issues**:
1. **Secret not found**: Re-run `./deploy/secrets-setup.sh`
2. **IAM permissions**: Check task execution role has `SecretsManagerReadWrite`
3. **Image pull failed**: Check ECR repository permissions

### Workers Not Processing Messages

1. **Check worker logs**:
   ```bash
   aws logs tail /ecs/sqs-search-segmenter-worker --follow
   ```

2. **Verify SQS permissions**: Task role needs `sqs:ReceiveMessage`, `sqs:DeleteMessage`

3. **Check queue visibility timeout**: Should be 900 seconds (15 minutes)

4. **Restart worker service**:
   ```bash
   aws ecs update-service \
     --cluster sqs-search-segmenter-cluster \
     --service sqs-search-segmenter-worker \
     --force-new-deployment \
     --region us-east-1
   ```

### High Memory/CPU Usage

1. **Check metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name CPUUtilization \
     --dimensions Name=ClusterName,Value=sqs-search-segmenter-cluster \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-01T23:59:59Z \
     --period 3600 \
     --statistics Average \
     --region us-east-1
   ```

2. **Increase task resources**: Edit `deploy/task-definitions.json` and redeploy

### Jobs Failing Repeatedly

1. **Check DLQ**:
   ```bash
   aws sqs receive-message \
     --queue-url $DLQ_URL \
     --max-number-of-messages 1 \
     --region us-east-1
   ```

2. **Review error logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name /ecs/sqs-search-segmenter-worker \
     --filter-pattern "FAILED" \
     --region us-east-1
   ```

3. **Common causes**:
   - Invalid manifestation_id
   - Neo4j/Milvus connection issues
   - Firebase authentication problems
   - Gemini API rate limits

## Cost Optimization

### Current Costs (Estimated)

**Minimal Setup** (1 API task + 2 Worker tasks):
- ECS Fargate: ~$75/month
  - API: 0.5 vCPU, 1GB RAM = ~$15/month
  - Workers: 1 vCPU, 2GB RAM × 2 = ~$60/month
- Application Load Balancer: ~$20/month
- ECR: ~$1/month (for image storage)
- CloudWatch Logs: ~$5/month (14 days retention)
- Secrets Manager: ~$1/month
- **Total: ~$100/month**

### Cost Reduction Strategies

1. **Use Fargate Spot** (up to 70% savings):
   - Edit service capacity provider to use `FARGATE_SPOT`
   - Suitable for fault-tolerant worker tasks

2. **Reduce task count during off-hours**:
   ```bash
   # Scale down at night
   aws ecs update-service \
     --cluster sqs-search-segmenter-cluster \
     --service sqs-search-segmenter-worker \
     --desired-count 1
   ```

3. **Optimize log retention**:
   ```bash
   # Reduce to 7 days
   aws logs put-retention-policy \
     --log-group-name /ecs/sqs-search-segmenter-worker \
     --retention-in-days 7
   ```

4. **Use smaller task sizes** (if possible):
   - Monitor actual CPU/memory usage
   - Adjust task definitions accordingly

## Updating the Application

### Deploy New Version

```bash
# Build and deploy new version
./deploy/deploy.sh

# Or just build without deploying
./deploy/deploy.sh --build-only

# Or deploy without rebuilding
./deploy/deploy.sh --deploy-only
```

### Rollback

```bash
# List previous task definitions
aws ecs list-task-definitions \
  --family-prefix sqs-search-segmenter-api \
  --region us-east-1

# Update service to previous version
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-api \
  --task-definition sqs-search-segmenter-api:REVISION \
  --region us-east-1
```

## Cleaning Up

To delete all resources and stop billing:

```bash
# Delete ECS services
aws ecs update-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-api \
  --desired-count 0 \
  --region us-east-1

aws ecs delete-service \
  --cluster sqs-search-segmenter-cluster \
  --service sqs-search-segmenter-api \
  --force \
  --region us-east-1

# Repeat for worker service...

# Delete cluster
aws ecs delete-cluster \
  --cluster sqs-search-segmenter-cluster \
  --region us-east-1

# Delete ALB (from AWS Console or CLI)
# Delete ECR repositories
# Delete Secrets Manager secrets
# Delete CloudWatch log groups
```

## Support

For issues or questions:

1. Check CloudWatch logs first
2. Review [Troubleshooting](#troubleshooting) section
3. Check AWS ECS service events in AWS Console
4. Contact the development team

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)

---

**Last Updated**: 2025-11-18  
**Version**: 1.0.0

