#!/bin/bash

###############################################################################
# AWS ECS Fargate Infrastructure Setup Script
#
# This script creates all the infrastructure needed for deploying the
# SQS Search Segmenter application on AWS ECS Fargate.
#
# Prerequisites:
#   - AWS CLI installed and configured (aws configure)
#   - jq installed (for JSON processing)
#   - IAM permissions for ECR, ECS, EC2, ELB, IAM, CloudWatch, Secrets Manager
#
# Usage:
#   ./deploy/ecs-setup.sh
#
###############################################################################

set -e  # Exit on error

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="sqs-search-segmenter"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
SERVICE_NAME_API="${PROJECT_NAME}-api"
SERVICE_NAME_WORKER="${PROJECT_NAME}-worker"
ECR_REPO_API="${PROJECT_NAME}-api"
ECR_REPO_WORKER="${PROJECT_NAME}-worker"
TASK_ROLE_NAME="${PROJECT_NAME}-task-role"
EXECUTION_ROLE_NAME="${PROJECT_NAME}-execution-role"
LOG_GROUP_API="/ecs/${SERVICE_NAME_API}"
LOG_GROUP_WORKER="/ecs/${SERVICE_NAME_WORKER}"

echo "=========================================="
echo "AWS ECS Fargate Infrastructure Setup"
echo "=========================================="
echo "Region: $REGION"
echo "Project: $PROJECT_NAME"
echo "=========================================="
echo

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed."
    echo "Please install it: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed."
    echo "Please install it: https://stedolan.github.io/jq/"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured."
    echo "Please run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✓ AWS Account ID: $ACCOUNT_ID"
echo

###############################################################################
# Step 1: Create ECR Repositories
###############################################################################
echo "Step 1: Creating ECR repositories..."

# Create API repository
aws ecr describe-repositories --repository-names "$ECR_REPO_API" --region "$REGION" &> /dev/null || \
    aws ecr create-repository \
        --repository-name "$ECR_REPO_API" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 > /dev/null

ECR_URI_API="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_API}"
echo "✓ API ECR Repository: $ECR_URI_API"

# Create Worker repository
aws ecr describe-repositories --repository-names "$ECR_REPO_WORKER" --region "$REGION" &> /dev/null || \
    aws ecr create-repository \
        --repository-name "$ECR_REPO_WORKER" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 > /dev/null

ECR_URI_WORKER="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_WORKER}"
echo "✓ Worker ECR Repository: $ECR_URI_WORKER"
echo

###############################################################################
# Step 2: Create CloudWatch Log Groups
###############################################################################
echo "Step 2: Creating CloudWatch Log Groups..."

aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_API" --region "$REGION" | grep -q "$LOG_GROUP_API" || \
    aws logs create-log-group --log-group-name "$LOG_GROUP_API" --region "$REGION"
echo "✓ API Log Group: $LOG_GROUP_API"

aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_WORKER" --region "$REGION" | grep -q "$LOG_GROUP_WORKER" || \
    aws logs create-log-group --log-group-name "$LOG_GROUP_WORKER" --region "$REGION"
echo "✓ Worker Log Group: $LOG_GROUP_WORKER"

# Set log retention (14 days)
aws logs put-retention-policy --log-group-name "$LOG_GROUP_API" --retention-in-days 14 --region "$REGION" || true
aws logs put-retention-policy --log-group-name "$LOG_GROUP_WORKER" --retention-in-days 14 --region "$REGION" || true
echo

###############################################################################
# Step 3: Create IAM Roles
###############################################################################
echo "Step 3: Creating IAM roles..."

# Task Execution Role (for ECS to pull images, write logs, access secrets)
cat > /tmp/ecs-execution-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create or update execution role
if ! aws iam get-role --role-name "$EXECUTION_ROLE_NAME" &> /dev/null; then
    aws iam create-role \
        --role-name "$EXECUTION_ROLE_NAME" \
        --assume-role-policy-document file:///tmp/ecs-execution-role-trust-policy.json \
        --region "$REGION" > /dev/null
    echo "✓ Created IAM Execution Role: $EXECUTION_ROLE_NAME"
else
    echo "✓ IAM Execution Role already exists: $EXECUTION_ROLE_NAME"
fi

# Attach AWS managed policies
aws iam attach-role-policy \
    --role-name "$EXECUTION_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy || true

# Create custom policy for Secrets Manager access
cat > /tmp/secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${PROJECT_NAME}/*"
    }
  ]
}
EOF

# Create or update the secrets policy
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${PROJECT_NAME}-secrets-access"
if ! aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
    aws iam create-policy \
        --policy-name "${PROJECT_NAME}-secrets-access" \
        --policy-document file:///tmp/secrets-policy.json \
        --region "$REGION" > /dev/null
    echo "✓ Created Secrets Manager policy"
else
    echo "✓ Secrets Manager policy already exists"
fi

aws iam attach-role-policy \
    --role-name "$EXECUTION_ROLE_NAME" \
    --policy-arn "$POLICY_ARN" || true

# Task Role (for application to access SQS, etc.)
if ! aws iam get-role --role-name "$TASK_ROLE_NAME" &> /dev/null; then
    aws iam create-role \
        --role-name "$TASK_ROLE_NAME" \
        --assume-role-policy-document file:///tmp/ecs-execution-role-trust-policy.json \
        --region "$REGION" > /dev/null
    echo "✓ Created IAM Task Role: $TASK_ROLE_NAME"
else
    echo "✓ IAM Task Role already exists: $TASK_ROLE_NAME"
fi

# Create custom policy for SQS access
cat > /tmp/task-policy.json <<EOF
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
      "Resource": "*"
    }
  ]
}
EOF

TASK_POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${PROJECT_NAME}-task-policy"
if ! aws iam get-policy --policy-arn "$TASK_POLICY_ARN" &> /dev/null; then
    aws iam create-policy \
        --policy-name "${PROJECT_NAME}-task-policy" \
        --policy-document file:///tmp/task-policy.json \
        --region "$REGION" > /dev/null
    echo "✓ Created Task policy"
else
    echo "✓ Task policy already exists"
fi

aws iam attach-role-policy \
    --role-name "$TASK_ROLE_NAME" \
    --policy-arn "$TASK_POLICY_ARN" || true

echo

###############################################################################
# Step 4: Create ECS Cluster
###############################################################################
echo "Step 4: Creating ECS cluster..."

if ! aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$REGION" | grep -q "ACTIVE"; then
    aws ecs create-cluster \
        --cluster-name "$CLUSTER_NAME" \
        --capacity-providers FARGATE FARGATE_SPOT \
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
        --region "$REGION" > /dev/null
    echo "✓ Created ECS Cluster: $CLUSTER_NAME"
else
    echo "✓ ECS Cluster already exists: $CLUSTER_NAME"
fi
echo

###############################################################################
# Step 5: Get Default VPC and Subnets
###############################################################################
echo "Step 5: Getting VPC information..."

DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region "$REGION")
echo "✓ Default VPC: $DEFAULT_VPC"

SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query 'Subnets[*].SubnetId' --output text --region "$REGION")
SUBNET_IDS=$(echo $SUBNETS | tr ' ' ',')
echo "✓ Subnets: $SUBNET_IDS"
echo

###############################################################################
# Step 6: Create Security Groups
###############################################################################
echo "Step 6: Creating security groups..."

# Security group for ALB
ALB_SG_NAME="${PROJECT_NAME}-alb-sg"
ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$ALB_SG_NAME" "Name=vpc-id,Values=$DEFAULT_VPC" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$REGION" 2>/dev/null)

if [ "$ALB_SG_ID" = "None" ] || [ -z "$ALB_SG_ID" ]; then
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name "$ALB_SG_NAME" \
        --description "Security group for ${PROJECT_NAME} ALB" \
        --vpc-id "$DEFAULT_VPC" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    
    # Allow HTTP and HTTPS from anywhere
    aws ec2 authorize-security-group-ingress \
        --group-id "$ALB_SG_ID" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" || true
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$ALB_SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region "$REGION" || true
    
    echo "✓ Created ALB Security Group: $ALB_SG_ID"
else
    echo "✓ ALB Security Group already exists: $ALB_SG_ID"
fi

# Security group for ECS tasks
ECS_SG_NAME="${PROJECT_NAME}-ecs-sg"
ECS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$ECS_SG_NAME" "Name=vpc-id,Values=$DEFAULT_VPC" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$REGION" 2>/dev/null)

if [ "$ECS_SG_ID" = "None" ] || [ -z "$ECS_SG_ID" ]; then
    ECS_SG_ID=$(aws ec2 create-security-group \
        --group-name "$ECS_SG_NAME" \
        --description "Security group for ${PROJECT_NAME} ECS tasks" \
        --vpc-id "$DEFAULT_VPC" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)
    
    # Allow traffic from ALB on port 8080
    aws ec2 authorize-security-group-ingress \
        --group-id "$ECS_SG_ID" \
        --protocol tcp \
        --port 8080 \
        --source-group "$ALB_SG_ID" \
        --region "$REGION" || true
    
    # Allow all outbound traffic (default, but explicitly set)
    echo "✓ Created ECS Security Group: $ECS_SG_ID"
else
    echo "✓ ECS Security Group already exists: $ECS_SG_ID"
fi
echo

###############################################################################
# Step 7: Create Application Load Balancer
###############################################################################
echo "Step 7: Creating Application Load Balancer..."

ALB_NAME="${PROJECT_NAME}-alb"
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names "$ALB_NAME" \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name "$ALB_NAME" \
        --subnets $(echo $SUBNETS) \
        --security-groups "$ALB_SG_ID" \
        --scheme internet-facing \
        --type application \
        --ip-address-type ipv4 \
        --region "$REGION" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)
    echo "✓ Created ALB: $ALB_ARN"
else
    echo "✓ ALB already exists: $ALB_ARN"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns "$ALB_ARN" \
    --query 'LoadBalancers[0].DNSName' \
    --output text \
    --region "$REGION")
echo "✓ ALB DNS: $ALB_DNS"

# Create Target Group
TG_NAME="${PROJECT_NAME}-api-tg"
TG_ARN=$(aws elbv2 describe-target-groups \
    --names "$TG_NAME" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$TG_ARN" = "None" ] || [ -z "$TG_ARN" ]; then
    TG_ARN=$(aws elbv2 create-target-group \
        --name "$TG_NAME" \
        --protocol HTTP \
        --port 8080 \
        --vpc-id "$DEFAULT_VPC" \
        --target-type ip \
        --health-check-enabled \
        --health-check-protocol HTTP \
        --health-check-path /health \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --region "$REGION" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
    echo "✓ Created Target Group: $TG_ARN"
else
    echo "✓ Target Group already exists: $TG_ARN"
fi

# Create Listener
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn "$ALB_ARN" \
    --query 'Listeners[0].ListenerArn' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

if [ "$LISTENER_ARN" = "None" ] || [ -z "$LISTENER_ARN" ]; then
    LISTENER_ARN=$(aws elbv2 create-listener \
        --load-balancer-arn "$ALB_ARN" \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
        --region "$REGION" \
        --query 'Listeners[0].ListenerArn' \
        --output text)
    echo "✓ Created Listener: $LISTENER_ARN"
else
    echo "✓ Listener already exists: $LISTENER_ARN"
fi
echo

###############################################################################
# Step 8: Save Configuration
###############################################################################
echo "Step 8: Saving configuration..."

cat > deploy/ecs-config.env <<EOF
# AWS Configuration
AWS_REGION=$REGION
AWS_ACCOUNT_ID=$ACCOUNT_ID

# ECR Repositories
ECR_REPO_API=$ECR_REPO_API
ECR_REPO_WORKER=$ECR_REPO_WORKER
ECR_URI_API=$ECR_URI_API
ECR_URI_WORKER=$ECR_URI_WORKER

# ECS Configuration
CLUSTER_NAME=$CLUSTER_NAME
SERVICE_NAME_API=$SERVICE_NAME_API
SERVICE_NAME_WORKER=$SERVICE_NAME_WORKER

# IAM Roles
TASK_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/${TASK_ROLE_NAME}
EXECUTION_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/${EXECUTION_ROLE_NAME}

# Network Configuration
VPC_ID=$DEFAULT_VPC
SUBNET_IDS=$SUBNET_IDS
ALB_SG_ID=$ALB_SG_ID
ECS_SG_ID=$ECS_SG_ID

# Load Balancer
ALB_ARN=$ALB_ARN
ALB_DNS=$ALB_DNS
TG_ARN=$TG_ARN

# CloudWatch Logs
LOG_GROUP_API=$LOG_GROUP_API
LOG_GROUP_WORKER=$LOG_GROUP_WORKER
EOF

echo "✓ Configuration saved to deploy/ecs-config.env"
echo

###############################################################################
# Summary
###############################################################################
echo "=========================================="
echo "✅ Infrastructure Setup Complete!"
echo "=========================================="
echo
echo "Summary:"
echo "--------"
echo "• ECR Repositories:"
echo "  - API: $ECR_URI_API"
echo "  - Worker: $ECR_URI_WORKER"
echo
echo "• ECS Cluster: $CLUSTER_NAME"
echo
echo "• Load Balancer:"
echo "  - DNS: $ALB_DNS"
echo "  - Access your API at: http://$ALB_DNS"
echo
echo "• CloudWatch Log Groups:"
echo "  - API: $LOG_GROUP_API"
echo "  - Worker: $LOG_GROUP_WORKER"
echo
echo "Next Steps:"
echo "-----------"
echo "1. Run ./deploy/secrets-setup.sh to configure secrets"
echo "2. Run ./deploy/deploy.sh to build and deploy your application"
echo
echo "=========================================="

