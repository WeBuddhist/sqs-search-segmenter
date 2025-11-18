#!/bin/bash

###############################################################################
# AWS Secrets Manager Setup Script
#
# This script helps you securely store all application credentials in
# AWS Secrets Manager for use with ECS Fargate.
#
# Prerequisites:
#   - AWS CLI installed and configured
#   - jq installed
#   - IAM permissions for Secrets Manager
#   - Your .env file with credentials
#
# Usage:
#   ./deploy/secrets-setup.sh
#
###############################################################################

set -e  # Exit on error

# Configuration
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="sqs-search-segmenter"
SECRET_PREFIX="${PROJECT_NAME}"

echo "=========================================="
echo "AWS Secrets Manager Setup"
echo "=========================================="
echo "Region: $REGION"
echo "Secret Prefix: $SECRET_PREFIX"
echo "=========================================="
echo

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured."
    exit 1
fi

echo "✓ Prerequisites met"
echo

###############################################################################
# Helper Functions
###############################################################################

create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" --region "$REGION" &> /dev/null; then
        # Update existing secret
        aws secretsmanager put-secret-value \
            --secret-id "$secret_name" \
            --secret-string "$secret_value" \
            --region "$REGION" > /dev/null
        echo "✓ Updated secret: $secret_name"
    else
        # Create new secret
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value" \
            --region "$REGION" > /dev/null
        echo "✓ Created secret: $secret_name"
    fi
}

prompt_for_value() {
    local var_name=$1
    local description=$2
    local is_sensitive=${3:-false}
    
    if [ "$is_sensitive" = "true" ]; then
        read -s -p "$description: " value
        echo
    else
        read -p "$description: " value
    fi
    
    echo "$value"
}

###############################################################################
# Load from .env if available
###############################################################################

if [ -f .env ]; then
    echo "Found .env file. Loading existing values..."
    source .env
    echo "✓ Loaded .env file"
    echo
else
    echo "No .env file found. You'll need to enter values manually."
    echo
fi

###############################################################################
# Collect Credentials
###############################################################################

echo "=========================================="
echo "Step 1: Collecting Credentials"
echo "=========================================="
echo "Press Enter to use values from .env (if shown), or type new values."
echo

# AWS Credentials
echo "--- AWS Credentials ---"
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    AWS_ACCESS_KEY_ID=$(prompt_for_value "AWS_ACCESS_KEY_ID" "AWS Access Key ID" false)
fi
echo "AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    AWS_SECRET_ACCESS_KEY=$(prompt_for_value "AWS_SECRET_ACCESS_KEY" "AWS Secret Access Key" true)
fi
echo "AWS_SECRET_ACCESS_KEY: ********"

if [ -z "$SQS_QUEUE_URL" ]; then
    SQS_QUEUE_URL=$(prompt_for_value "SQS_QUEUE_URL" "SQS Queue URL" false)
fi
echo "SQS_QUEUE_URL: $SQS_QUEUE_URL"
echo

# Neo4j Credentials
echo "--- Neo4j Credentials ---"
if [ -z "$NEO4J_URI" ]; then
    NEO4J_URI=$(prompt_for_value "NEO4J_URI" "Neo4j URI (e.g., bolt://host:7687)" false)
fi
echo "NEO4J_URI: $NEO4J_URI"

if [ -z "$NEO4J_USER" ]; then
    NEO4J_USER=$(prompt_for_value "NEO4J_USER" "Neo4j Username" false)
fi
echo "NEO4J_USER: $NEO4J_USER"

if [ -z "$NEO4J_PASSWORD" ]; then
    NEO4J_PASSWORD=$(prompt_for_value "NEO4J_PASSWORD" "Neo4j Password" true)
fi
echo "NEO4J_PASSWORD: ********"
echo

# Milvus Credentials
echo "--- Milvus Credentials ---"
if [ -z "$MILVUS_URI" ]; then
    MILVUS_URI=$(prompt_for_value "MILVUS_URI" "Milvus URI" false)
fi
echo "MILVUS_URI: $MILVUS_URI"

if [ -z "$MILVUS_TOKEN" ]; then
    MILVUS_TOKEN=$(prompt_for_value "MILVUS_TOKEN" "Milvus Token" true)
fi
echo "MILVUS_TOKEN: ********"

if [ -z "$MILVUS_COLLECTION_NAME" ]; then
    MILVUS_COLLECTION_NAME=$(prompt_for_value "MILVUS_COLLECTION_NAME" "Milvus Collection Name" false)
fi
echo "MILVUS_COLLECTION_NAME: $MILVUS_COLLECTION_NAME"
echo

# Firebase Credentials
echo "--- Firebase Credentials ---"
if [ -z "$FIREBASE_STORAGE_BUCKET" ]; then
    FIREBASE_STORAGE_BUCKET=$(prompt_for_value "FIREBASE_STORAGE_BUCKET" "Firebase Storage Bucket" false)
fi
echo "FIREBASE_STORAGE_BUCKET: $FIREBASE_STORAGE_BUCKET"

# For Firebase credentials, we need the JSON file content
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS_JSON" ]; then
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo "Found Firebase credentials file: $GOOGLE_APPLICATION_CREDENTIALS"
        GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat "$GOOGLE_APPLICATION_CREDENTIALS")
    else
        echo "Enter path to Firebase service account JSON file:"
        read -p "Path: " firebase_creds_path
        if [ -f "$firebase_creds_path" ]; then
            GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat "$firebase_creds_path")
        else
            echo "ERROR: File not found: $firebase_creds_path"
            exit 1
        fi
    fi
fi
echo "Firebase Credentials: Loaded"
echo

# Gemini API Key
echo "--- Gemini API ---"
if [ -z "$GEMINI_API_KEY" ]; then
    GEMINI_API_KEY=$(prompt_for_value "GEMINI_API_KEY" "Gemini API Key" true)
fi
echo "GEMINI_API_KEY: ********"
echo

###############################################################################
# Step 2: Store Secrets in AWS Secrets Manager
###############################################################################

echo "=========================================="
echo "Step 2: Storing Secrets in AWS Secrets Manager"
echo "=========================================="
echo

# Store individual secrets
create_or_update_secret \
    "${SECRET_PREFIX}/aws-access-key-id" \
    "$AWS_ACCESS_KEY_ID" \
    "AWS Access Key ID for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/aws-secret-access-key" \
    "$AWS_SECRET_ACCESS_KEY" \
    "AWS Secret Access Key for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/sqs-queue-url" \
    "$SQS_QUEUE_URL" \
    "SQS Queue URL for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/neo4j-uri" \
    "$NEO4J_URI" \
    "Neo4j URI for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/neo4j-user" \
    "$NEO4J_USER" \
    "Neo4j Username for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/neo4j-password" \
    "$NEO4J_PASSWORD" \
    "Neo4j Password for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/milvus-uri" \
    "$MILVUS_URI" \
    "Milvus URI for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/milvus-token" \
    "$MILVUS_TOKEN" \
    "Milvus Token for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/milvus-collection-name" \
    "$MILVUS_COLLECTION_NAME" \
    "Milvus Collection Name for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/firebase-storage-bucket" \
    "$FIREBASE_STORAGE_BUCKET" \
    "Firebase Storage Bucket for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/firebase-credentials" \
    "$GOOGLE_APPLICATION_CREDENTIALS_JSON" \
    "Firebase Service Account JSON for ${PROJECT_NAME}"

create_or_update_secret \
    "${SECRET_PREFIX}/gemini-api-key" \
    "$GEMINI_API_KEY" \
    "Gemini API Key for ${PROJECT_NAME}"

echo

###############################################################################
# Step 3: Generate Secret ARNs for Task Definitions
###############################################################################

echo "=========================================="
echo "Step 3: Generating Secret ARNs"
echo "=========================================="
echo

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > deploy/secrets-arns.env <<EOF
# Secret ARNs for ECS Task Definitions
# These will be used in task-definitions.json

AWS_ACCESS_KEY_ID_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/aws-access-key-id
AWS_SECRET_ACCESS_KEY_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/aws-secret-access-key
SQS_QUEUE_URL_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/sqs-queue-url
NEO4J_URI_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/neo4j-uri
NEO4J_USER_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/neo4j-user
NEO4J_PASSWORD_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/neo4j-password
MILVUS_URI_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/milvus-uri
MILVUS_TOKEN_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/milvus-token
MILVUS_COLLECTION_NAME_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/milvus-collection-name
FIREBASE_STORAGE_BUCKET_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/firebase-storage-bucket
FIREBASE_CREDENTIALS_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/firebase-credentials
GEMINI_API_KEY_ARN=arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${SECRET_PREFIX}/gemini-api-key
EOF

echo "✓ Secret ARNs saved to deploy/secrets-arns.env"
echo

###############################################################################
# Summary
###############################################################################

echo "=========================================="
echo "✅ Secrets Setup Complete!"
echo "=========================================="
echo
echo "Stored ${12} secrets in AWS Secrets Manager:"
echo "  • AWS credentials (access key, secret key, SQS URL)"
echo "  • Neo4j credentials (URI, user, password)"
echo "  • Milvus credentials (URI, token, collection name)"
echo "  • Firebase credentials (bucket, service account JSON)"
echo "  • Gemini API key"
echo
echo "Secret ARNs saved to: deploy/secrets-arns.env"
echo
echo "Next Steps:"
echo "-----------"
echo "1. Verify secrets in AWS Console:"
echo "   https://console.aws.amazon.com/secretsmanager/home?region=${REGION}"
echo
echo "2. Run ./deploy/deploy.sh to build and deploy your application"
echo
echo "=========================================="

