#!/bin/bash
set -e

# Deploy script - builds and pushes Docker image to ECR, updates Lambda functions
# Usage: ./deploy.sh

REGION="us-east-1"
TERRAFORM_DIR="terraform"

echo "==> Getting config from terraform..."
cd "$TERRAFORM_DIR"

ECR_URL=$(terraform output -raw ecr_repository_url)
WORKER_FUNCTION=$(terraform output -raw worker_function_name)
ENQUEUE_FUNCTION="${WORKER_FUNCTION%-worker}-enqueue"

cd ..

echo "    ECR: $ECR_URL"
echo "    Worker: $WORKER_FUNCTION"
echo "    Enqueue: $ENQUEUE_FUNCTION"

echo ""
echo "==> Logging into ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URL"

echo ""
echo "==> Building Docker image..."
docker build --provenance=false --platform linux/amd64 -t "$ECR_URL:latest" .

echo ""
echo "==> Pushing to ECR..."
docker push "$ECR_URL:latest"

echo ""
echo "==> Updating Lambda functions..."
aws lambda update-function-code \
    --function-name "$WORKER_FUNCTION" \
    --image-uri "$ECR_URL:latest" \
    --region "$REGION" \
    --no-cli-pager

aws lambda update-function-code \
    --function-name "$ENQUEUE_FUNCTION" \
    --image-uri "$ECR_URL:latest" \
    --region "$REGION" \
    --no-cli-pager

echo ""
echo "==> Deploying frontend to Cloudflare Pages..."
# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
npx wrangler pages deploy frontend/ --project-name=creatives-dealogic

echo ""
echo "==> Done! Lambdas and frontend updated."
