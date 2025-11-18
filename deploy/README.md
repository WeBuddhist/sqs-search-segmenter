# Deployment Scripts

This directory contains scripts and configuration for deploying to AWS ECS Fargate.

## Files

### Setup Scripts (Run Once)

1. **ecs-setup.sh** - Creates AWS infrastructure
   - ECR repositories for Docker images
   - ECS cluster (Fargate)
   - Application Load Balancer
   - Security groups
   - IAM roles
   - CloudWatch log groups

2. **secrets-setup.sh** - Stores credentials securely
   - Prompts for all sensitive credentials
   - Stores them in AWS Secrets Manager
   - Generates secret ARNs for task definitions

### Configuration Files

3. **task-definitions.json** - ECS task definitions template
   - API service configuration (0.5 vCPU, 1GB RAM)
   - Worker service configuration (1 vCPU, 2GB RAM)
   - Environment variables and secret references

### Deployment Script (Run for Each Update)

4. **deploy.sh** - Main deployment automation
   - Builds Docker images
   - Pushes to ECR
   - Registers task definitions
   - Creates/updates ECS services
   - Waits for deployment completion

### Generated Files (Not in Git)

After running the setup scripts, these files are generated:

- `ecs-config.env` - Infrastructure configuration (ECR URIs, security groups, etc.)
- `secrets-arns.env` - Secret ARNs for task definitions

## Usage

### First Time Setup

```bash
# 1. Create infrastructure
./deploy/ecs-setup.sh

# 2. Store secrets
./deploy/secrets-setup.sh

# 3. Deploy application
./deploy/deploy.sh
```

### Subsequent Deployments

```bash
# Build and deploy changes
./deploy/deploy.sh

# Or just build (no deploy)
./deploy/deploy.sh --build-only

# Or just deploy (no build)
./deploy/deploy.sh --deploy-only
```

## Documentation

- **QUICK_START.md** - Fast deployment guide (15 minutes)
- **../README_DEPLOYMENT.md** - Complete deployment documentation

## Prerequisites

- AWS CLI configured (`aws configure`)
- Docker installed and running
- `jq` and `envsubst` installed
- IAM permissions for ECR, ECS, ALB, IAM, Secrets Manager, CloudWatch

## Architecture

```
deploy/
├── ecs-setup.sh           # Infrastructure setup
├── secrets-setup.sh       # Secrets management
├── task-definitions.json  # ECS task configs
├── deploy.sh              # Main deployment
├── QUICK_START.md         # Quick reference
├── README.md              # This file
├── ecs-config.env         # Generated: Infrastructure config
└── secrets-arns.env       # Generated: Secret ARNs
```

## Troubleshooting

**"aws: command not found"**
- Install AWS CLI: https://aws.amazon.com/cli/

**"jq: command not found"**
- Install jq: `brew install jq` (macOS)

**"Permission denied"**
- Make scripts executable: `chmod +x deploy/*.sh`

**"Access Denied" errors**
- Check IAM permissions for ECR, ECS, Secrets Manager

**Deployment fails**
- Check CloudWatch logs: `aws logs tail /ecs/sqs-search-segmenter-api --follow`
- Verify secrets exist: `aws secretsmanager list-secrets --region us-east-1`

## Support

For detailed troubleshooting, see:
- [README_DEPLOYMENT.md](../README_DEPLOYMENT.md) - Full documentation
- [QUICK_START.md](QUICK_START.md) - Quick reference

