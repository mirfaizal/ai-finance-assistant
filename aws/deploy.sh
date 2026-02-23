#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy.sh  –  Build, push, and deploy AI Finance Assistant to AWS ECS Fargate
#
# Prerequisites:
#   • AWS CLI installed and configured (aws configure)
#   • Docker running locally
#   • ECR repos already created (see aws/README.md)
#   • ECS cluster + service already created
#
# Usage:
#   ./aws/deploy.sh                          # uses defaults below
#   AWS_REGION=eu-west-1 ./aws/deploy.sh    # override region
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

BACKEND_REPO="ai-finance-backend"
FRONTEND_REPO="ai-finance-frontend"
ECS_CLUSTER="${ECS_CLUSTER:-ai-finance-cluster}"
ECS_SERVICE="${ECS_SERVICE:-ai-finance-service}"
TASK_FAMILY="ai-finance-assistant"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "═══════════════════════════════════════════════════════"
echo " AI Finance Assistant – AWS ECS Deployment"
echo " Account : ${AWS_ACCOUNT_ID}"
echo " Region  : ${AWS_REGION}"
echo " Cluster : ${ECS_CLUSTER}"
echo " Service : ${ECS_SERVICE}"
echo "═══════════════════════════════════════════════════════"

# ── Step 1: Authenticate Docker with ECR ──────────────────────────────────────
echo ""
echo "▶ Authenticating with ECR…"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# ── Step 2: Build backend image ───────────────────────────────────────────────
echo ""
echo "▶ Building backend image…"
docker build \
  --platform linux/amd64 \
  -f "${PROJECT_ROOT}/Dockerfile.backend" \
  -t "${BACKEND_REPO}:latest" \
  "${PROJECT_ROOT}"

# Tag and push backend
docker tag "${BACKEND_REPO}:latest" "${ECR_REGISTRY}/${BACKEND_REPO}:latest"
echo "▶ Pushing backend image…"
docker push "${ECR_REGISTRY}/${BACKEND_REPO}:latest"

# ── Step 3: Build frontend image ──────────────────────────────────────────────
echo ""
echo "▶ Building frontend image (production build)…"
FRONTEND_DIR="${PROJECT_ROOT}/src/web_app/frontend"
docker build \
  --platform linux/amd64 \
  -f "${FRONTEND_DIR}/Dockerfile.frontend" \
  --build-arg VITE_API_BASE_URL="" \
  -t "${FRONTEND_REPO}:latest" \
  "${FRONTEND_DIR}"

# Tag and push frontend
docker tag "${FRONTEND_REPO}:latest" "${ECR_REGISTRY}/${FRONTEND_REPO}:latest"
echo "▶ Pushing frontend image…"
docker push "${ECR_REGISTRY}/${FRONTEND_REPO}:latest"

# ── Step 4: Register updated task definition ──────────────────────────────────
echo ""
echo "▶ Registering task definition…"
TASK_DEF_FILE="${SCRIPT_DIR}/task-definition.json"

# Replace placeholders with real values
TMP_TASK_DEF=$(mktemp)
sed \
  -e "s|<ACCOUNT_ID>|${AWS_ACCOUNT_ID}|g" \
  -e "s|<REGION>|${AWS_REGION}|g" \
  "${TASK_DEF_FILE}" > "${TMP_TASK_DEF}"

NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json "file://${TMP_TASK_DEF}" \
  --query "taskDefinition.taskDefinitionArn" \
  --output text)
rm -f "${TMP_TASK_DEF}"

echo "  Registered: ${NEW_TASK_DEF_ARN}"

# ── Step 5: Update ECS service ────────────────────────────────────────────────
echo ""
echo "▶ Updating ECS service to use new task definition…"
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --task-definition "${NEW_TASK_DEF_ARN}" \
  --force-new-deployment \
  --output table

# ── Step 6: Wait for rollout ──────────────────────────────────────────────────
echo ""
echo "▶ Waiting for service to stabilize (this may take 2–5 minutes)…"
aws ecs wait services-stable \
  --cluster "${ECS_CLUSTER}" \
  --services "${ECS_SERVICE}"

echo ""
echo "✅ Deployment complete!"
echo "   Check your ALB or ECS console for the public endpoint."
