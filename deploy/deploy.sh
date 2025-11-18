#!/bin/bash

###############################################################################
# AWS ECS Fargate Deployment Script
#
# This script builds Docker images, pushes them to ECR, and deploys/updates
# ECS services.
#
# Prerequisites:
#   - Docker installed and running
#   - AWS CLI configured
#   - ./deploy/ecs-setup.sh has been run
#   - ./deploy/secrets-setup.sh has been run
#
# Usage:
#   ./deploy/deploy.sh [--build-only] [--deploy-only]
#
###############################################################################

set -e  # Exit on error

# Parse arguments
BUILD_ONLY=false
DEPLOY_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--build-only] [--deploy-only]"
            exit 1
            ;;
    esac
done

# Load configuration
if [ ! -f deploy/ecs-config.env ]; then
    echo "ERROR: deploy/ecs-config.env not found."
    echo "Please run ./deploy/ecs-setup.sh first."
    exit 1
fi

source deploy/ecs-config.env

if [ ! -f deploy/secrets-arns.env ]; then
    echo "ERROR: deploy/secrets-arns.env not found."
    echo "Please run ./deploy/secrets-setup.sh first."
    exit 1
fi

source deploy/secrets-arns.env

echo "=========================================="
echo "AWS ECS Fargate Deployment"
echo "=========================================="
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "=========================================="
echo

# Get version tag
if [ -d .git ]; then
    VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
else
    VERSION="latest"
fi

echo "Version tag: $VERSION"
echo

###############################################################################
# Step 1: Build Docker Images
###############################################################################

if [ "$DEPLOY_ONLY" = false ]; then
    echo "=========================================="
    echo "Step 1: Building Docker Images"
    echo "=========================================="
    echo

    # Build API image
    echo "Building API image..."
    docker build -t "$ECR_REPO_API:$VERSION" -t "$ECR_REPO_API:latest" .
    echo "✓ Built $ECR_REPO_API:$VERSION"

    # Build Worker image (same Dockerfile, different command)
    echo "Building Worker image..."
    docker build -t "$ECR_REPO_WORKER:$VERSION" -t "$ECR_REPO_WORKER:latest" .
    echo "✓ Built $ECR_REPO_WORKER:$VERSION"
    echo

    ###########################################################################
    # Step 2: Push to ECR
    ###########################################################################

    echo "=========================================="
    echo "Step 2: Pushing Images to ECR"
    echo "=========================================="
    echo

    # Login to ECR
    echo "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    echo "✓ Logged in to ECR"

    # Tag and push API image
    echo "Pushing API image..."
    docker tag "$ECR_REPO_API:$VERSION" "$ECR_URI_API:$VERSION"
    docker tag "$ECR_REPO_API:latest" "$ECR_URI_API:latest"
    docker push "$ECR_URI_API:$VERSION"
    docker push "$ECR_URI_API:latest"
    echo "✓ Pushed $ECR_URI_API:$VERSION"

    # Tag and push Worker image
    echo "Pushing Worker image..."
    docker tag "$ECR_REPO_WORKER:$VERSION" "$ECR_URI_WORKER:$VERSION"
    docker tag "$ECR_REPO_WORKER:latest" "$ECR_URI_WORKER:latest"
    docker push "$ECR_URI_WORKER:$VERSION"
    docker push "$ECR_URI_WORKER:latest"
    echo "✓ Pushed $ECR_URI_WORKER:$VERSION"
    echo

    if [ "$BUILD_ONLY" = true ]; then
        echo "=========================================="
        echo "✅ Build Complete (--build-only flag set)"
        echo "=========================================="
        exit 0
    fi
fi

###############################################################################
# Step 3: Register Task Definitions
###############################################################################

echo "=========================================="
echo "Step 3: Registering Task Definitions"
echo "=========================================="
echo

# Helper function to substitute environment variables in JSON
substitute_vars() {
    local template=$1
    
    # Read the template and substitute variables
    local result=$(cat "$template")
    
    # Substitute all variables
    result=$(echo "$result" | envsubst)
    
    echo "$result"
}

# Register API task definition
echo "Registering API task definition..."
API_TASK_DEF=$(jq '.api' deploy/task-definitions.json)
API_TASK_DEF=$(echo "$API_TASK_DEF" | envsubst)
echo "$API_TASK_DEF" > /tmp/api-task-def.json

aws ecs register-task-definition \
    --cli-input-json file:///tmp/api-task-def.json \
    --region "$AWS_REGION" > /dev/null

API_TASK_DEF_ARN=$(aws ecs describe-task-definition \
    --task-definition sqs-search-segmenter-api \
    --region "$AWS_REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✓ Registered API task definition: $API_TASK_DEF_ARN"

# Register Worker task definition
echo "Registering Worker task definition..."
WORKER_TASK_DEF=$(jq '.worker' deploy/task-definitions.json)
WORKER_TASK_DEF=$(echo "$WORKER_TASK_DEF" | envsubst)
echo "$WORKER_TASK_DEF" > /tmp/worker-task-def.json

aws ecs register-task-definition \
    --cli-input-json file:///tmp/worker-task-def.json \
    --region "$AWS_REGION" > /dev/null

WORKER_TASK_DEF_ARN=$(aws ecs describe-task-definition \
    --task-definition sqs-search-segmenter-worker \
    --region "$AWS_REGION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✓ Registered Worker task definition: $WORKER_TASK_DEF_ARN"
echo

###############################################################################
# Step 4: Create or Update ECS Services
###############################################################################

echo "=========================================="
echo "Step 4: Creating/Updating ECS Services"
echo "=========================================="
echo

# Convert subnet IDs to array format for AWS CLI
SUBNET_ARRAY=$(echo $SUBNET_IDS | tr ',' ' ')

# Check if API service exists
if aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME_API" \
    --region "$AWS_REGION" 2>/dev/null | grep -q "ACTIVE"; then
    
    echo "Updating existing API service..."
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME_API" \
        --task-definition "$API_TASK_DEF_ARN" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null
    echo "✓ Updated API service"
else
    echo "Creating new API service..."
    aws ecs create-service \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME_API" \
        --task-definition "$API_TASK_DEF_ARN" \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TG_ARN,containerName=api,containerPort=8080" \
        --health-check-grace-period-seconds 60 \
        --region "$AWS_REGION" > /dev/null
    echo "✓ Created API service"
fi

# Check if Worker service exists
if aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME_WORKER" \
    --region "$AWS_REGION" 2>/dev/null | grep -q "ACTIVE"; then
    
    echo "Updating existing Worker service..."
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME_WORKER" \
        --task-definition "$WORKER_TASK_DEF_ARN" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null
    echo "✓ Updated Worker service"
else
    echo "Creating new Worker service..."
    aws ecs create-service \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME_WORKER" \
        --task-definition "$WORKER_TASK_DEF_ARN" \
        --desired-count 2 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
        --region "$AWS_REGION" > /dev/null
    echo "✓ Created Worker service (2 tasks = 8 workers)"
fi

echo

###############################################################################
# Step 5: Wait for Deployment
###############################################################################

echo "=========================================="
echo "Step 5: Waiting for Deployment"
echo "=========================================="
echo

echo "Waiting for API service to stabilize..."
aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME_API" \
    --region "$AWS_REGION"
echo "✓ API service is stable"

echo "Waiting for Worker service to stabilize..."
aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME_WORKER" \
    --region "$AWS_REGION"
echo "✓ Worker service is stable"

echo

###############################################################################
# Summary
###############################################################################

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo
echo "Services:"
echo "---------"
echo "• API Service: $SERVICE_NAME_API (1 task)"
echo "• Worker Service: $SERVICE_NAME_WORKER (2 tasks = 8 parallel workers)"
echo
echo "Access your API:"
echo "----------------"
echo "• URL: http://$ALB_DNS"
echo "• Health Check: http://$ALB_DNS/health"
echo "• API Docs: http://$ALB_DNS/docs"
echo
echo "Monitoring:"
echo "-----------"
echo "• View API logs:"
echo "  aws logs tail $LOG_GROUP_API --follow --region $AWS_REGION"
echo
echo "• View Worker logs:"
echo "  aws logs tail $LOG_GROUP_WORKER --follow --region $AWS_REGION"
echo
echo "• Check service status:"
echo "  aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME_API $SERVICE_NAME_WORKER --region $AWS_REGION"
echo
echo "• Monitor SQS queue:"
echo "  aws sqs get-queue-attributes --queue-url \$SQS_QUEUE_URL --attribute-names All --region $AWS_REGION"
echo
echo "Scaling:"
echo "--------"
echo "• Scale API service:"
echo "  aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME_API --desired-count 2 --region $AWS_REGION"
echo
echo "• Scale Worker service:"
echo "  aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME_WORKER --desired-count 4 --region $AWS_REGION"
echo "  (4 tasks = 16 parallel workers)"
echo
echo "Test your deployment:"
echo "---------------------"
echo "curl -X POST http://$ALB_DNS/jobs/create \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"manifestation_id\": \"test-123\"}'"
echo
echo "=========================================="

