#!/bin/bash
# Build and push AutoGLM container to ECR

set -e

REPO_NAME="autoglm-vllm-byoc"
REGION=${AWS_REGION:-"us-east-2"}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest"

echo "Building AutoGLM container..."
echo "Account: ${ACCOUNT_ID}"
echo "Region: ${REGION}"
echo "Image URI: ${IMAGE_URI}"

# Create ECR repository if not exists
aws ecr describe-repositories --repository-names ${REPO_NAME} --region ${REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION}

# Login to ECR
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Build and push
docker build -t ${REPO_NAME}:latest .
docker tag ${REPO_NAME}:latest ${IMAGE_URI}
docker push ${IMAGE_URI}

echo "Done! Image URI: ${IMAGE_URI}"
