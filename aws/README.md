# AWS Deployment Guide

This guide walks you through deploying the AI Finance Assistant to **AWS ECS Fargate** from scratch.

## Architecture

```
Internet
    │
    ▼
Application Load Balancer (ALB)
    │  :80  (or :443 with ACM cert)
    ▼
ECS Service  (FARGATE, awsvpc)
    ├── frontend container  (nginx :80)
    └── backend  container  (uvicorn :8000)
          │
          └── EFS mount  →  /app/data/conversations.db  (SQLite)
```

Both containers run inside the **same ECS task** so nginx can proxy to `localhost:8000` — or they can be separate tasks if you prefer independent scaling.

---

## Prerequisites

| Tool | Version |
|------|---------|
| AWS CLI | ≥ 2.x |
| Docker  | ≥ 24.x |
| jq      | any    |

Configure your AWS credentials:

```bash
aws configure
# or: export AWS_PROFILE=my-profile
```

---

## Step 1 – Create ECR Repositories

```bash
aws ecr create-repository --repository-name ai-finance-backend  --region us-east-1
aws ecr create-repository --repository-name ai-finance-frontend --region us-east-1
```

---

## Step 2 – Store API Keys in Secrets Manager

```bash
# OpenAI
aws secretsmanager create-secret \
  --name ai-finance/openai-api-key \
  --secret-string '{"OPENAI_API_KEY":"sk-proj-..."}'

# Tavily
aws secretsmanager create-secret \
  --name ai-finance/tavily-api-key \
  --secret-string '{"TAVILY_API_KEY":"tvly-..."}'

# Pinecone
aws secretsmanager create-secret \
  --name ai-finance/pinecone-api-key \
  --secret-string '{"PINECONE_API_KEY":"..."}'
```

> **Note:** Update the ARNs in `task-definition.json` if you use different secret names.

---

## Step 3 – Create EFS for SQLite Persistence

```bash
# Create file system
EFS_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --encrypted \
  --query 'FileSystemId' --output text)
echo "EFS ID: $EFS_ID"

# Create a mount target in your subnet (replace subnet/sg IDs)
aws efs create-mount-target \
  --file-system-id "$EFS_ID" \
  --subnet-id subnet-XXXXXXXX \
  --security-groups sg-XXXXXXXX

# Create the directory for our data
aws efs create-access-point \
  --file-system-id "$EFS_ID" \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory "Path=/ai-finance/data,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755}"
```

Replace `<EFS_FILESYSTEM_ID>` in `task-definition.json` with `$EFS_ID`.

---

## Step 4 – Create IAM Roles

### ecsTaskExecutionRole
Must have:
- `AmazonECSTaskExecutionRolePolicy` (managed)
- `secretsmanager:GetSecretValue` on your secrets
- `logs:CreateLogGroup` + `logs:CreateLogStream` + `logs:PutLogEvents`

### ecsTaskRole (optional extra permissions)
- `elasticfilesystem:ClientMount`, `ClientWrite` for EFS access

---

## Step 5 – Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/ai-finance-backend
aws logs create-log-group --log-group-name /ecs/ai-finance-frontend
```

---

## Step 6 – Create ECS Cluster & Service

```bash
# Cluster
aws ecs create-cluster --cluster-name ai-finance-cluster

# Service (adjust subnet / security-group / ALB target-group ARN)
aws ecs create-service \
  --cluster ai-finance-cluster \
  --service-name ai-finance-service \
  --task-definition ai-finance-assistant \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-XXX],securityGroups=[sg-XXX],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=frontend,containerPort=80"
```

---

## Step 7 – Deploy

After completing the above setup, every subsequent deploy is just:

```bash
chmod +x aws/deploy.sh

# Optional overrides:
# export AWS_ACCOUNT_ID=123456789012
# export AWS_REGION=us-east-1
# export ECS_CLUSTER=ai-finance-cluster
# export ECS_SERVICE=ai-finance-service

./aws/deploy.sh
```

The script will:
1. Authenticate Docker with ECR
2. Build & push both images (linux/amd64)
3. Register a new task definition revision
4. Update the ECS service with `--force-new-deployment`
5. Wait for the service to stabilize

---

## Useful Commands

```bash
# View running tasks
aws ecs list-tasks --cluster ai-finance-cluster

# Tail logs (backend)
aws logs tail /ecs/ai-finance-backend --follow

# Tail logs (frontend)
aws logs tail /ecs/ai-finance-frontend --follow

# SSH into a running container (ECS Exec)
aws ecs execute-command \
  --cluster ai-finance-cluster \
  --task <TASK_ID> \
  --container backend \
  --interactive \
  --command "/bin/bash"
```
