# Quick Start Guide

This guide will help you get the MCP Image Generator up and running quickly.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured
- [ ] Docker installed
- [ ] Python 3.11+ installed
- [ ] Git installed

## 5-Minute Setup (Local Testing)

### 1. Clone and Setup

```bash
# Clone the repository (or create the files)
cd mcp-image-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify access
aws sts get-caller-identity
```

### 3. Enable Bedrock Models

```bash
# Open Bedrock console
# Navigate to: https://console.aws.amazon.com/bedrock/
# Go to "Model access" → "Manage model access"
# Enable: Stability AI SDXL 1.0 and Amazon Titan Image Generator
```

### 4. Create S3 Bucket

```bash
# Replace YOUR_UNIQUE_ID with something unique
export S3_BUCKET=agentcore-generated-images-$(date +%s)

aws s3 mb s3://$S3_BUCKET --region us-east-1
```

### 5. Create Guardrail

```bash
# Create a basic guardrail
cat > guardrail-config.json << 'EOF'
{
  "name": "ImageContentFilter",
  "description": "Filters inappropriate content",
  "contentPolicyConfig": {
    "filtersConfig": [
      {
        "type": "SEXUAL",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "VIOLENCE",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      }
    ]
  },
  "blockedInputMessaging": "I cannot generate inappropriate images."
}
EOF

# Create the guardrail
aws bedrock create-guardrail \
  --cli-input-json file://guardrail-config.json \
  --region us-east-1

# Save the guardrail ID from the output
export GUARDRAIL_ID=<your-guardrail-id>
```

### 6. Set Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
# Update: S3_BUCKET, GUARDRAIL_ID
```

### 7. Run Locally

```bash
# Using Docker Compose (recommended)
docker-compose up

# OR using Python directly
python -m src.server
```

### 8. Test the Server

```bash
# Health check
curl http://localhost:8080/health

# Generate an image
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset",
    "model": "stability"
  }'

# Test guardrail (should be blocked)
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "violent content",
    "model": "stability"
  }'
```

## Deploy to AWS (Production)

### 1. Create IAM Role

```bash
# Create trust policy
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name AgentcoreImageGenRole \
  --assume-role-policy-document file://trust-policy.json
```

### 2. Attach Permissions

```bash
# Attach AWS managed policies
aws iam attach-role-policy \
  --role-name AgentcoreImageGenRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-role-policy \
  --role-name AgentcoreImageGenRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# For production, use custom policies with least privilege (see README.md)
```

### 3. Deploy to ECR and Agentcore

```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy
./deploy.sh

# To deploy to Agentcore Runtime
export DEPLOY_TO_AGENTCORE=true
./deploy.sh
```

### 4. Integrate with QuickSight Q Suite

1. Open Amazon QuickSight Console
2. Navigate to Q Suite → Agents
3. Create or select an agent
4. Add Action → Custom Action → MCP Server
5. Enter your Agentcore Runtime endpoint
6. Configure authentication
7. Test the integration

## Common Commands

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Stop service
docker-compose down

# Rebuild image
docker-compose build --no-cache

# Run tests
pytest tests/ -v

# Check code style
black src/ tests/
flake8 src/ tests/
```

## Verification Checklist

- [ ] Server starts without errors
- [ ] Health check returns "healthy"
- [ ] Can generate image with safe prompt
- [ ] Guardrail blocks inappropriate prompts
- [ ] Image is uploaded to S3
- [ ] Presigned URL is accessible
- [ ] Image can be viewed in browser

## Next Steps

1. Review the full README.md for detailed configuration
2. Check architecture-diagram.md for system overview
3. Set up monitoring in CloudWatch
4. Configure rate limiting
5. Implement caching for better performance
6. Set up CI/CD pipeline

## Getting Help

- Check logs: `docker-compose logs`
- Review CloudWatch logs in AWS Console
- See troubleshooting section in README.md
- Check AWS service health dashboard

## Cost Estimate

For testing (10 images):
- Bedrock: ~$0.40
- S3: ~$0.01
- Other services: ~$0.10
- **Total: ~$0.51**

For production (1000 images/month):
- See cost breakdown in architecture-diagram.md
- **Estimated: ~$96/month**

## Security Reminders

- Never commit .env file
- Use IAM roles instead of access keys in production
- Enable MFA on AWS account
- Regularly rotate credentials
- Review CloudTrail logs
- Enable S3 bucket encryption
- Use VPC endpoints for AWS services

## Support

For issues or questions:
1. Check the README.md troubleshooting section
2. Review AWS service documentation
3. Check CloudWatch logs for errors
4. Verify IAM permissions
5. Test each component individually
