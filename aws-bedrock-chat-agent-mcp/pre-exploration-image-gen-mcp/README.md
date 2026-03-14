# MCP Server on AWS Agentcore Runtime with Image Generation and Guardrails

## Overview

This project implements a Model Context Protocol (MCP) server hosted on AWS Agentcore Runtime that generates images using AWS Bedrock models while enforcing content safety through AWS Agentcore Guardrails. Generated images are stored in S3 and accessible via presigned URLs.

## Architecture

See `architecture-diagram.md` for a detailed visual representation of the system components and data flow.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Python 3.11 or higher
- Docker (for local testing)
- Basic knowledge of AWS services

## AWS Services Used

1. **AWS Agentcore Runtime** - Hosts the MCP server
2. **AWS Bedrock** - Image generation using Stability AI or Amazon Titan models
3. **AWS Agentcore Guardrails** - Content filtering and safety checks
4. **Amazon S3** - Storage for generated images
5. **AWS IAM** - Access management and permissions
6. **Amazon CloudWatch** - Logging and monitoring
7. **Amazon QuickSight** - Integration with Q Suite Agents

## Project Structure

```
mcp-image-generator/
├── src/
│   ├── __init__.py
│   ├── server.py
│   ├── bedrock_client.py
│   ├── guardrail_client.py
│   ├── s3_client.py
│   └── utils.py
├── tests/
│   ├── __init__.py
│   └── test_server.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── config.yaml
├── deploy.sh
├── README.md
└── architecture-diagram.md
```

## Step-by-Step Implementation Guide

Continue reading for detailed implementation steps...


### Phase 1: AWS Account Setup and IAM Configuration

#### Step 1.1: Create IAM Role for Agentcore Runtime

```bash
# Create trust policy for Agentcore Runtime
cat > trust-policy.json << EOF
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

# Create the IAM role
aws iam create-role \
  --role-name AgentcoreImageGenRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for Agentcore Runtime MCP Server"
```

#### Step 1.2: Create IAM Policy with Required Permissions

```bash
cat > agentcore-permissions.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/stability.stable-diffusion-xl-v1",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-image-generator-v1"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ApplyGuardrail"
      ],
      "Resource": "arn:aws:bedrock:*:*:guardrail/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::agentcore-generated-images/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
  --policy-name AgentcoreImageGenPolicy \
  --policy-document file://agentcore-permissions.json

# Replace YOUR_ACCOUNT_ID with your actual AWS account ID
aws iam attach-role-policy \
  --role-name AgentcoreImageGenRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/AgentcoreImageGenPolicy
```

### Phase 2: AWS Bedrock Setup

#### Step 2.1: Enable Bedrock Model Access

1. Navigate to AWS Bedrock Console (https://console.aws.amazon.com/bedrock/)
2. Go to "Model access" in the left sidebar
3. Click "Manage model access"
4. Enable the following models:
   - Stability AI SDXL 1.0
   - Amazon Titan Image Generator G1
5. Submit the access request (usually instant approval)

#### Step 2.2: Create Bedrock Guardrail

```bash
# Create guardrail configuration
cat > guardrail-config.json << EOF
{
  "name": "ImageGenerationContentFilter",
  "description": "Filters violent, obscene, and adult content requests",
  "topicPolicyConfig": {
    "topicsConfig": [
      {
        "name": "Violence",
        "definition": "Content depicting violence, gore, weapons, or harm",
        "examples": [
          "Generate an image of someone being hurt",
          "Create a violent scene",
          "Show weapons or combat"
        ],
        "type": "DENY"
      },
      {
        "name": "AdultContent",
        "definition": "Sexually explicit or suggestive content",
        "examples": [
          "Generate nude images",
          "Create adult content",
          "Explicit imagery"
        ],
        "type": "DENY"
      },
      {
        "name": "ObsceneContent",
        "definition": "Offensive, disturbing, or inappropriate content",
        "examples": [
          "Generate disturbing imagery",
          "Create offensive content",
          "Shocking or grotesque images"
        ],
        "type": "DENY"
      }
    ]
  },
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
      },
      {
        "type": "HATE",
        "inputStrength": "MEDIUM",
        "outputStrength": "MEDIUM"
      },
      {
        "type": "INSULTS",
        "inputStrength": "MEDIUM",
        "outputStrength": "MEDIUM"
      }
    ]
  },
  "blockedInputMessaging": "I cannot generate images with violent, adult, or obscene content. Please provide a different request.",
  "blockedOutputsMessaging": "The generated content was blocked due to safety concerns."
}
EOF

# Create the guardrail
aws bedrock create-guardrail \
  --cli-input-json file://guardrail-config.json \
  --region us-east-1

# Note the guardrail ID and version from the output - you'll need these later
```

### Phase 3: S3 Bucket Setup

#### Step 3.1: Create S3 Bucket for Generated Images

```bash
# Create S3 bucket (bucket names must be globally unique)
aws s3 mb s3://agentcore-generated-images-YOUR_UNIQUE_ID --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket agentcore-generated-images-YOUR_UNIQUE_ID \
  --versioning-configuration Status=Enabled

# Configure bucket policy for presigned URLs
cat > bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAgentcoreAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/AgentcoreImageGenRole"
      },
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::agentcore-generated-images-YOUR_UNIQUE_ID/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket agentcore-generated-images-YOUR_UNIQUE_ID \
  --policy file://bucket-policy.json

# Configure lifecycle policy to delete old images after 30 days
cat > lifecycle-policy.json << EOF
{
  "Rules": [
    {
      "Id": "DeleteOldImages",
      "Status": "Enabled",
      "Expiration": {
        "Days": 30
      },
      "Filter": {
        "Prefix": ""
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket agentcore-generated-images-YOUR_UNIQUE_ID \
  --lifecycle-configuration file://lifecycle-policy.json
```

### Phase 4: MCP Server Implementation

See the implementation files in the `src/` directory for the complete code.

### Phase 5: Deployment to AWS Agentcore Runtime

#### Step 5.1: Package the MCP Server

```bash
# Build Docker image
docker build -t mcp-image-generator:latest .

# Create ECR repository
aws ecr create-repository --repository-name mcp-image-generator --region us-east-1

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push image
docker tag mcp-image-generator:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mcp-image-generator:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mcp-image-generator:latest
```

#### Step 5.2: Deploy to Agentcore Runtime

```bash
# Create Agentcore Runtime configuration
cat > agentcore-config.json << EOF
{
  "name": "ImageGeneratorMCPServer",
  "description": "MCP server for safe image generation",
  "runtime": {
    "type": "CONTAINER",
    "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mcp-image-generator:latest",
    "port": 8080,
    "environment": {
      "AWS_REGION": "us-east-1",
      "S3_BUCKET": "agentcore-generated-images-YOUR_UNIQUE_ID",
      "GUARDRAIL_ID": "YOUR_GUARDRAIL_ID",
      "GUARDRAIL_VERSION": "1"
    }
  },
  "executionRole": "arn:aws:iam::YOUR_ACCOUNT_ID:role/AgentcoreImageGenRole",
  "networking": {
    "vpcConfig": {
      "securityGroupIds": ["sg-xxxxx"],
      "subnetIds": ["subnet-xxxxx", "subnet-yyyyy"]
    }
  }
}
EOF

# Deploy to Agentcore Runtime
aws agentcore create-runtime \
  --cli-input-json file://agentcore-config.json \
  --region us-east-1
```

### Phase 6: Amazon QuickSight Q Suite Integration

#### Step 6.1: Register MCP Server as Q Suite Action

1. Navigate to Amazon QuickSight Console
2. Go to Q Suite → Agents
3. Click "Create Agent" or select existing agent
4. Under "Actions", click "Add Action"
5. Select "Custom Action" → "MCP Server"
6. Enter the Agentcore Runtime endpoint URL
7. Configure authentication using IAM role
8. Test the connection

#### Step 6.2: Configure Action Parameters

The MCP server exposes a `generate_image` tool with the following parameters:

```json
{
  "actionName": "generate_image",
  "description": "Generate an image based on user description",
  "parameters": {
    "prompt": {
      "type": "string",
      "description": "Description of the image to generate",
      "required": true
    },
    "model": {
      "type": "string",
      "description": "Model to use (stability or titan)",
      "default": "stability",
      "enum": ["stability", "titan"]
    },
    "width": {
      "type": "integer",
      "description": "Image width",
      "default": 1024
    },
    "height": {
      "type": "integer",
      "description": "Image height",
      "default": 1024
    }
  }
}
```

### Phase 7: Testing and Validation

#### Step 7.1: Local Testing

```bash
# Run locally with Docker Compose
docker-compose up

# Test the MCP server with a safe prompt
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset",
    "model": "stability"
  }'
```

#### Step 7.2: Test Guardrails

```bash
# This should be blocked by the guardrail
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate violent content",
    "model": "stability"
  }'

# Expected response:
# {
#   "error": "Content blocked by guardrail",
#   "message": "I cannot generate images with violent, adult, or obscene content."
# }
```

#### Step 7.3: End-to-End Testing in Q Suite

1. Open Amazon QuickSight Q Suite chat
2. Type: "Generate an image of a peaceful garden with flowers"
3. Verify the agent calls the MCP server action
4. Check that the image URL is returned
5. Verify the image is accessible from S3

### Phase 8: Monitoring and Maintenance

#### Step 8.1: CloudWatch Dashboards

Create a CloudWatch dashboard to monitor:
- Request count
- Guardrail block rate
- Image generation latency
- S3 upload success rate
- Error rates

#### Step 8.2: Set Up Alarms

```bash
# Create alarm for guardrail blocks
aws cloudwatch put-metric-alarm \
  --alarm-name HighGuardrailBlockRate \
  --alarm-description "Alert when guardrail block rate is high" \
  --metric-name GuardrailBlocks \
  --namespace MCP/ImageGenerator \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Configuration Reference

### Environment Variables

- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET`: S3 bucket name for images
- `GUARDRAIL_ID`: Bedrock guardrail ID
- `GUARDRAIL_VERSION`: Guardrail version
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `PRESIGNED_URL_EXPIRY`: URL expiry in seconds (default: 3600)

### Model Configuration

**Stability AI SDXL 1.0:**
- Model ID: `stability.stable-diffusion-xl-v1`
- Max dimensions: 1024x1024
- Supported styles: photographic, digital-art, cinematic, etc.

**Amazon Titan Image Generator:**
- Model ID: `amazon.titan-image-generator-v1`
- Max dimensions: 1024x1024
- Built-in content filtering

## Troubleshooting

### Common Issues

1. **Guardrail not blocking content**
   - Verify guardrail version is correct
   - Check guardrail configuration in Bedrock console
   - Review CloudWatch logs for guardrail evaluation results

2. **S3 upload failures**
   - Verify IAM role has PutObject permissions
   - Check bucket policy allows the role
   - Ensure bucket exists in the correct region

3. **Bedrock model access denied**
   - Confirm model access is enabled in Bedrock console
   - Verify IAM role has InvokeModel permissions
   - Check if model is available in your region

4. **Agentcore Runtime deployment fails**
   - Verify ECR image is accessible
   - Check VPC and security group configuration
   - Review execution role permissions

## Security Best Practices

1. Use least privilege IAM policies
2. Enable S3 bucket encryption at rest
3. Use VPC endpoints for AWS service access
4. Rotate credentials regularly
5. Enable CloudTrail for audit logging
6. Implement rate limiting on the MCP server
7. Use presigned URLs with short expiry times
8. Enable MFA for AWS console access

## Cost Optimization

1. Use S3 lifecycle policies to delete old images
2. Implement caching for repeated prompts
3. Use Bedrock on-demand pricing initially
4. Monitor usage with AWS Cost Explorer
5. Set up billing alarms
6. Consider Reserved Capacity for high usage

## Next Steps

1. Implement caching layer (Redis/ElastiCache)
2. Add support for image editing and variations
3. Implement batch image generation
4. Add webhook notifications for async processing
5. Create admin dashboard for monitoring
6. Implement user quotas and rate limiting
7. Add support for additional Bedrock models

## Support and Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Agentcore Runtime Guide](https://docs.aws.amazon.com/agentcore/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Amazon QuickSight Q Suite](https://docs.aws.amazon.com/quicksight/)

## License

MIT License
