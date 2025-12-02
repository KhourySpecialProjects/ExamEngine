#!/bin/bash

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="466814372088"
BACKEND_REPO="fastapi-backend"
FRONTEND_REPO="next-web"
ALB_DNS="examengine-dev-1894900913.us-east-1.elb.amazonaws.com"

echo "🔐 Authenticating Docker to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo ""
echo "🏗️  Building backend image..."
cd /home/alex123/CS/ExamEngine
docker build -t ${BACKEND_REPO}:latest -f backend/Dockerfile .

echo ""
echo "📦 Tagging backend image..."
docker tag ${BACKEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:latest

echo ""
echo "⬆️  Pushing backend image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:latest

echo ""
echo "🏗️  Building frontend image..."
docker build -t ${FRONTEND_REPO}:latest \
  --build-arg NEXT_PUBLIC_API_URL="http://${ALB_DNS}/api" \
  -f frontend/Dockerfile .

echo ""
echo "📦 Tagging frontend image..."
docker tag ${FRONTEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:latest

echo ""
echo "⬆️  Pushing frontend image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:latest

echo ""
echo "✅ Done! Both images have been built and pushed to ECR."

