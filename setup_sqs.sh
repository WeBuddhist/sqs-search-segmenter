#!/bin/bash

###############################################################################
# AWS SQS Setup Script for Segmentation Workers
#
# This script creates:
# 1. Dead Letter Queue (DLQ) for failed messages
# 2. Main processing queue with retry policy
# 3. Configures visibility timeout and message retention
#
# Usage:
#   ./setup_sqs.sh
#
# Prerequisites:
#   - AWS CLI installed and configured (aws configure)
#   - Appropriate IAM permissions to create SQS queues
###############################################################################

set -e  # Exit on error

# Configuration
REGION="${AWS_REGION:-us-east-1}"
QUEUE_NAME="${SQS_QUEUE_NAME:-segmentation-processing-queue}"
DLQ_NAME="${SQS_DLQ_NAME:-segmentation-dlq}"

# Queue Settings
VISIBILITY_TIMEOUT=900          # 15 minutes (adjust based on job duration)
MESSAGE_RETENTION_PERIOD=345600 # 4 days
RECEIVE_WAIT_TIME=20            # Long polling: 20 seconds
MAX_RETRIES=5                   # Number of retries before sending to DLQ

echo "=========================================="
echo "AWS SQS Setup for Segmentation Workers"
echo "=========================================="
echo "Region: $REGION"
echo "Main Queue: $QUEUE_NAME"
echo "DLQ: $DLQ_NAME"
echo "Max Retries: $MAX_RETRIES"
echo "Visibility Timeout: ${VISIBILITY_TIMEOUT}s ($(($VISIBILITY_TIMEOUT / 60)) minutes)"
echo "=========================================="
echo

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed."
    echo "Please install it: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials are configured
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured."
    echo "Please run: aws configure"
    exit 1
fi

echo "✓ AWS credentials configured"
echo

###############################################################################
# Step 1: Create Dead Letter Queue (DLQ)
###############################################################################
echo "Step 1: Creating Dead Letter Queue..."

DLQ_URL=$(aws sqs create-queue \
    --queue-name "$DLQ_NAME" \
    --region "$REGION" \
    --attributes "{
        \"MessageRetentionPeriod\": \"$MESSAGE_RETENTION_PERIOD\",
        \"ReceiveMessageWaitTimeSeconds\": \"$RECEIVE_WAIT_TIME\"
    }" \
    --query 'QueueUrl' \
    --output text 2>/dev/null || true)

if [ -z "$DLQ_URL" ]; then
    # Queue might already exist, try to get URL
    echo "  Queue might already exist, fetching URL..."
    DLQ_URL=$(aws sqs get-queue-url \
        --queue-name "$DLQ_NAME" \
        --region "$REGION" \
        --query 'QueueUrl' \
        --output text)
fi

echo "✓ DLQ URL: $DLQ_URL"
echo

# Get DLQ ARN (needed for redrive policy)
DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url "$DLQ_URL" \
    --region "$REGION" \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)

echo "✓ DLQ ARN: $DLQ_ARN"
echo

###############################################################################
# Step 2: Create Main Processing Queue with Redrive Policy
###############################################################################
echo "Step 2: Creating Main Processing Queue..."

# Redrive policy: After MAX_RETRIES failed attempts, send to DLQ
REDRIVE_POLICY=$(cat <<EOF
{
    "deadLetterTargetArn": "$DLQ_ARN",
    "maxReceiveCount": $MAX_RETRIES
}
EOF
)

MAIN_QUEUE_URL=$(aws sqs create-queue \
    --queue-name "$QUEUE_NAME" \
    --region "$REGION" \
    --attributes "{
        \"VisibilityTimeout\": \"$VISIBILITY_TIMEOUT\",
        \"MessageRetentionPeriod\": \"$MESSAGE_RETENTION_PERIOD\",
        \"ReceiveMessageWaitTimeSeconds\": \"$RECEIVE_WAIT_TIME\",
        \"RedrivePolicy\": $(echo "$REDRIVE_POLICY" | jq -c .)
    }" \
    --query 'QueueUrl' \
    --output text 2>/dev/null || true)

if [ -z "$MAIN_QUEUE_URL" ]; then
    # Queue might already exist, try to get URL and update attributes
    echo "  Queue might already exist, fetching URL and updating attributes..."
    MAIN_QUEUE_URL=$(aws sqs get-queue-url \
        --queue-name "$QUEUE_NAME" \
        --region "$REGION" \
        --query 'QueueUrl' \
        --output text)
    
    # Update attributes
    aws sqs set-queue-attributes \
        --queue-url "$MAIN_QUEUE_URL" \
        --region "$REGION" \
        --attributes "{
            \"VisibilityTimeout\": \"$VISIBILITY_TIMEOUT\",
            \"MessageRetentionPeriod\": \"$MESSAGE_RETENTION_PERIOD\",
            \"ReceiveMessageWaitTimeSeconds\": \"$RECEIVE_WAIT_TIME\",
            \"RedrivePolicy\": $(echo "$REDRIVE_POLICY" | jq -c .)
        }"
fi

echo "✓ Main Queue URL: $MAIN_QUEUE_URL"
echo

###############################################################################
# Step 3: Display Configuration Summary
###############################################################################
echo "=========================================="
echo "✅ SQS Setup Complete!"
echo "=========================================="
echo
echo "Configuration Summary:"
echo "----------------------"
echo "Main Queue URL: $MAIN_QUEUE_URL"
echo "DLQ URL: $DLQ_URL"
echo "Region: $REGION"
echo
echo "Queue Settings:"
echo "  - Visibility Timeout: ${VISIBILITY_TIMEOUT}s ($(($VISIBILITY_TIMEOUT / 60)) minutes)"
echo "  - Message Retention: ${MESSAGE_RETENTION_PERIOD}s ($(($MESSAGE_RETENTION_PERIOD / 86400)) days)"
echo "  - Max Retries: $MAX_RETRIES"
echo "  - Long Polling: ${RECEIVE_WAIT_TIME}s"
echo
echo "How It Works:"
echo "-------------"
echo "1. Messages are sent to the main queue"
echo "2. Workers poll and process messages"
echo "3. If processing fails, message returns to queue after visibility timeout"
echo "4. After $MAX_RETRIES failed attempts, message moves to DLQ"
echo "5. Monitor DLQ for persistent failures requiring manual intervention"
echo
echo "Next Steps:"
echo "-----------"
echo "1. Add this to your .env file:"
echo "   SQS_QUEUE_URL=$MAIN_QUEUE_URL"
echo "   AWS_REGION=$REGION"
echo
echo "2. Ensure your IAM user/role has these permissions:"
echo "   - sqs:SendMessage (for API to enqueue jobs)"
echo "   - sqs:ReceiveMessage (for workers to poll)"
echo "   - sqs:DeleteMessage (for workers to remove processed messages)"
echo "   - sqs:ChangeMessageVisibility (for extending processing time)"
echo
echo "3. Start your services:"
echo "   docker-compose up -d"
echo
echo "4. Monitor queues:"
echo "   aws sqs get-queue-attributes --queue-url $MAIN_QUEUE_URL --attribute-names All --region $REGION"
echo "   aws sqs get-queue-attributes --queue-url $DLQ_URL --attribute-names All --region $REGION"
echo
echo "=========================================="

