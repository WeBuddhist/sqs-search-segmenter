# Multi-Environment Deployment Guide for Render

This guide explains how to deploy the SQS Search Segmenter to multiple environments (DEV, TEST, PROD) on Render.

## Overview

The application uses environment-specific configuration that automatically picks up the correct credentials based on the `ENVIRONMENT` variable. All environment variables should be prefixed with `DEV_`, `TEST_`, or `PROD_`.

## Architecture

```
config.py reads ENVIRONMENT variable → Determines prefix → Loads {PREFIX}_{VAR_NAME}
```

For example:
- If `ENVIRONMENT=dev`, it loads `DEV_NEO4J_URI`
- If `ENVIRONMENT=prod`, it loads `PROD_NEO4J_URI`
- If `ENVIRONMENT=test`, it loads `TEST_NEO4J_URI`

## Deployment Steps

### 1. Create Separate Services on Render

Create three separate Web Services or Background Workers:

1. **sqs-segmenter-dev** (Development)
2. **sqs-segmenter-test** (Testing)
3. **sqs-segmenter-prod** (Production)

### 2. Configure Environment Variables

For each service, configure the variables as follows:

#### Development Service (sqs-segmenter-dev)

**Critical Variable:**
```
ENVIRONMENT=dev
```

**AWS Configuration:**
```
DEV_AWS_REGION=us-east-1
DEV_AWS_ACCESS_KEY_ID=your-dev-aws-key
DEV_AWS_SECRET_ACCESS_KEY=your-dev-aws-secret
DEV_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../dev-queue
```

**Neo4j Configuration:**
```
DEV_NEO4J_URI=bolt://dev-neo4j-host:7687
DEV_NEO4J_USER=neo4j
DEV_NEO4J_PASSWORD=your-dev-password
```

**Milvus Configuration:**
```
DEV_MILVUS_URI=https://dev-milvus.com
DEV_MILVUS_TOKEN=your-dev-token
DEV_MILVUS_COLLECTION_NAME=dev_collection
```

**Firebase Configuration:**
```
DEV_FIREBASE_STORAGE_BUCKET=dev-bucket.appspot.com
DEV_GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-dev-credentials.json
```

**Optional (Non-environment-specific):**
```
GEMINI_API_KEY=your-gemini-key
LOG_LEVEL=DEBUG
```

#### Testing Service (sqs-segmenter-test)

**Critical Variable:**
```
ENVIRONMENT=test
```

Then set all variables with `TEST_` prefix:
```
TEST_AWS_REGION=us-east-1
TEST_AWS_ACCESS_KEY_ID=your-test-aws-key
TEST_AWS_SECRET_ACCESS_KEY=your-test-aws-secret
TEST_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../test-queue
TEST_NEO4J_URI=bolt://test-neo4j-host:7687
TEST_NEO4J_USER=neo4j
TEST_NEO4J_PASSWORD=your-test-password
TEST_MILVUS_URI=https://test-milvus.com
TEST_MILVUS_TOKEN=your-test-token
TEST_MILVUS_COLLECTION_NAME=test_collection
TEST_FIREBASE_STORAGE_BUCKET=test-bucket.appspot.com
TEST_GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-test-credentials.json
```

#### Production Service (sqs-segmenter-prod)

**Critical Variable:**
```
ENVIRONMENT=prod
```

Then set all variables with `PROD_` prefix:
```
PROD_AWS_REGION=us-east-1
PROD_AWS_ACCESS_KEY_ID=your-prod-aws-key
PROD_AWS_SECRET_ACCESS_KEY=your-prod-aws-secret
PROD_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../prod-queue
PROD_NEO4J_URI=bolt://prod-neo4j-host:7687
PROD_NEO4J_USER=neo4j
PROD_NEO4J_PASSWORD=your-prod-password
PROD_MILVUS_URI=https://prod-milvus.com
PROD_MILVUS_TOKEN=your-prod-token
PROD_MILVUS_COLLECTION_NAME=prod_collection
PROD_FIREBASE_STORAGE_BUCKET=prod-bucket.appspot.com
PROD_GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-prod-credentials.json
```

### 3. Secret Files (Firebase Credentials)

For each service, you'll need to upload the Firebase service account JSON as a Secret File:

1. Go to your Render service → Settings → Secret Files
2. Add Secret File:
   - **Development:** `/etc/secrets/firebase-dev-credentials.json`
   - **Testing:** `/etc/secrets/firebase-test-credentials.json`
   - **Production:** `/etc/secrets/firebase-prod-credentials.json`

### 4. Deployment Configuration

Each service should have the same build and start commands:

**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
python app/worker.py
```

## Quick Setup Script

You can use this script to list all environment variables needed for a specific environment:

```bash
# Generate variable list for an environment
./deploy/generate_env_vars.sh dev   # or test, or prod
```

## Verification

After deployment, verify the configuration is loaded correctly:

1. Check the logs for: `Starting in {ENVIRONMENT} environment`
2. Verify it's connecting to the correct databases
3. Test with a sample SQS message

## Troubleshooting

### Wrong environment variables loaded
- Check `ENVIRONMENT` variable is set correctly (must be lowercase: `dev`, `test`, or `prod`)
- Verify all variables have the correct prefix (`DEV_`, `TEST_`, or `PROD_`)

### Missing credentials
- Ensure all required variables are set with the appropriate prefix
- Check Secret Files are uploaded correctly
- Verify file paths match in `{ENV}_GOOGLE_APPLICATION_CREDENTIALS`

### Service connects to wrong database
- Double-check the `ENVIRONMENT` variable on the service
- Verify the prefixed variables point to the correct resources

## Best Practices

1. **Never mix environments** - Always use environment-specific queues, databases, and storage buckets
2. **Use different AWS accounts** - Ideally, dev/test/prod should use separate AWS accounts
3. **Separate Milvus collections** - Use different collection names per environment
4. **Isolate Neo4j databases** - Use separate Neo4j instances or databases
5. **Monitor each environment** - Set up alerts for each service independently
6. **Test promotion path** - Always test changes in dev → test → prod order

## Environment Variable Checklist

Use this checklist when setting up a new environment:

- [ ] `ENVIRONMENT` set to correct value
- [ ] All AWS credentials prefixed correctly
- [ ] Neo4j credentials prefixed correctly
- [ ] Milvus credentials prefixed correctly
- [ ] Firebase storage bucket prefixed correctly
- [ ] Firebase credentials JSON uploaded as Secret File
- [ ] `{ENV}_GOOGLE_APPLICATION_CREDENTIALS` path matches Secret File path
- [ ] `GEMINI_API_KEY` set (if using)
- [ ] `LOG_LEVEL` set appropriately (DEBUG for dev, INFO for prod)

## Additional Resources

- [Render Environment Variables Guide](https://render.com/docs/environment-variables)
- [Render Secret Files Guide](https://render.com/docs/secret-files)
- [SQS Setup Guide](../docs/SQS_SETUP.md)

