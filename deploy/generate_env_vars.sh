#!/bin/bash

# Script to generate environment variable list for a specific environment
# Usage: ./generate_env_vars.sh [dev|test|prod]

if [ $# -eq 0 ]; then
    echo "Usage: $0 [dev|test|prod]"
    echo "Example: $0 dev"
    exit 1
fi

ENV=$1

# Convert to uppercase for prefix
PREFIX=$(echo "$ENV" | tr '[:lower:]' '[:upper:]')

echo "=================================================="
echo "Environment Variables for ${ENV} Environment"
echo "=================================================="
echo ""
echo "Copy these variable names to your Render service:"
echo ""
echo "# Critical Variable"
echo "ENVIRONMENT=${ENV}"
echo ""
echo "# AWS Configuration"
echo "${PREFIX}_AWS_REGION="
echo "${PREFIX}_AWS_ACCESS_KEY_ID="
echo "${PREFIX}_AWS_SECRET_ACCESS_KEY="
echo "${PREFIX}_SQS_QUEUE_URL="
echo ""
echo "# Neo4j Configuration"
echo "${PREFIX}_NEO4J_URI="
echo "${PREFIX}_NEO4J_USER="
echo "${PREFIX}_NEO4J_PASSWORD="
echo ""
echo "# Milvus Configuration"
echo "${PREFIX}_MILVUS_URI="
echo "${PREFIX}_MILVUS_TOKEN="
echo "${PREFIX}_MILVUS_COLLECTION_NAME="
echo ""
echo "# Firebase Configuration"
echo "${PREFIX}_FIREBASE_STORAGE_BUCKET="
echo "${PREFIX}_GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-${ENV}-credentials.json"
echo ""
echo "# Optional (Non-environment-specific)"
echo "GEMINI_API_KEY="
echo "LOG_LEVEL=INFO"
echo ""
echo "=================================================="
echo "Secret File to Upload:"
echo "=================================================="
echo "Path: /etc/secrets/firebase-${ENV}-credentials.json"
echo "Content: Your Firebase service account JSON for ${ENV}"
echo "=================================================="

