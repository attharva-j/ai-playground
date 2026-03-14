#!/bin/bash

# Deployment script for MCP Image Generator to AWS Agentcore Runtime
# This script automates the build, push, and deployment process

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPOSITORY_NAME="mcp-image-generator"
IMAGE_TAG=${IMAGE_TAG:-latest}

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Get AWS account ID
print_info "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $AWS_ACCOUNT_ID"

# ECR repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

# Step 1: Create ECR repository if it doesn't exist
print_info "Checking if ECR repository exists..."
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION &> /dev/null; then
    print_info "Creating ECR repository..."
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    print_info "ECR repository created successfully"
else
    print_info "ECR repository already exists"
fi

# Step 2: Authenticate Docker to ECR
print_info "Authenticating Docker to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

# Step 3: Build Docker image
print_info "Building Docker image..."
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .
print_info "Docker image built successfully"

# Step 4: Tag image for ECR
print_info "Tagging image for ECR..."
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $ECR_URI:$(date +%Y%m%d-%H%M%S)

# Step 5: Push image to ECR
print_info "Pushing image to ECR..."
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:$(date +%Y%m%d-%H%M%S)
print_info "Image pushed successfully"

# Step 6: Deploy to Agentcore Runtime (if configured)
if [ -n "$DEPLOY_TO_AGENTCORE" ]; then
    print_info "Deploying to AWS Agentcore Runtime..."
    
    # Check if runtime exists
    RUNTIME_NAME="ImageGeneratorMCPServer"
    
    if aws agentcore describe-runtime --runtime-name $RUNTIME_NAME --region $AWS_REGION &> /dev/null; then
        print_info "Updating existing runtime..."
        aws agentcore update-runtime \
            --runtime-name $RUNTIME_NAME \
            --image $ECR_URI:$IMAGE_TAG \
            --region $AWS_REGION
    else
        print_info "Creating new runtime..."
        aws agentcore create-runtime \
            --cli-input-json file://agentcore-config.json \
            --region $AWS_REGION
    fi
    
    print_info "Deployment to Agentcore Runtime completed"
else
    print_warning "DEPLOY_TO_AGENTCORE not set. Skipping Agentcore deployment."
    print_info "To deploy to Agentcore, set DEPLOY_TO_AGENTCORE=true and ensure agentcore-config.json is configured"
fi

# Step 7: Print summary
print_info "Deployment completed successfully!"
echo ""
echo "Summary:"
echo "  ECR Repository: $ECR_URI"
echo "  Image Tag: $IMAGE_TAG"
echo "  Region: $AWS_REGION"
echo ""
echo "To test locally:"
echo "  docker run -p 8080:8080 --env-file .env $ECR_REPOSITORY_NAME:$IMAGE_TAG"
echo ""
echo "To deploy to Agentcore Runtime:"
echo "  export DEPLOY_TO_AGENTCORE=true"
echo "  ./deploy.sh"
