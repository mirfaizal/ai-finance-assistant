# Installation & Deployment Guide

This guide covers two environments:

- [Local Development](#part-1-local-development) — Mac / Linux / Windows
- [AWS Deployment](#part-2-aws-deployment) — ECS Fargate (recommended), EC2, and Lambda options

---

## Part 1: Local Development

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | `python --version` to check |
| pip | Latest | Comes with Python |
| Node.js | 18+ | Only needed for the React frontend |
| npm | 9+ | Bundled with Node.js |
| OpenAI API key | — | https://platform.openai.com/api-keys |
| Git | Any | To clone the repo |

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/mirfaizal/ai-finance-assistant-svc.git
cd ai-finance-assistant-svc/ai_finance_assistant
```

---

### Step 2 — Create a Python virtual environment

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

### Step 3 — Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Key packages installed:

| Package | Purpose |
|---|---|
| `openai>=1.0.0` | OpenAI client for all 6 agents |
| `fastapi>=0.110.0` | REST API framework |
| `uvicorn[standard]>=0.27.0` | ASGI server |
| `langgraph` | LangGraph StateGraph orchestration |
| `pydantic` | Data validation & serialization |
| `python-dotenv>=1.0.0` | Load `.env` file |
| `pyyaml>=6.0` | Parse `config.yaml` |
| `pytest>=8.0.0` | Test runner |
| `httpx>=0.27.0` | Async HTTP client (FastAPI TestClient) |

---

### Step 4 — Configure environment variables

Copy the example env file and fill in your keys:

```bash
cp .env .env.backup    # keep a backup of the template
```

Edit `.env`:

```env
# ── Required ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-proj-...your-openai-key-here...

# ── Tavily Web Search (real-time data) ────────────────────────────────────────
# Free tier: 1 000 searches/month at https://tavily.com
# Without this, agents answer from LLM training data only (no live data).
TAVILY_API_KEY=tvly-...

# ── Pinecone Vector Store (RAG) ───────────────────────────────────────────────
# Create a free Serverless index at https://app.pinecone.io
# Index must use dimension=1536 (text-embedding-ada-002 embeddings).
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX=ai-finance-rag

# ── LangSmith Observability (optional) ───────────────────────────────────────
# Free tier at https://smith.langchain.com — traces every agent call
# Set to false (or omit) to disable tracing completely.
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=ai-finance-assistant
```

> **Minimum to run:** only `OPENAI_API_KEY` is required. Tavily, Pinecone, and LangSmith are all optional — agents degrade gracefully if those keys are missing.

**Getting API keys:**

| Service | Where to get it | Free tier |
|---|---|---|
| OpenAI | https://platform.openai.com/api-keys | Pay-per-use |
| Tavily | https://tavily.com → "Get API key" | 1 000 searches/month |
| Pinecone | https://app.pinecone.io → API Keys | 1 free Serverless index |
| LangSmith | https://smith.langchain.com → Settings → API Keys | Free developer tier |

---

### Step 5 — (Optional) Adjust `config.yaml`

```yaml
openai:
  model: gpt-4o-mini     # cheaper alternative; change to gpt-4.1 for best quality
  temperature: 0.3

server:
  host: "0.0.0.0"
  port: 8000
```

---

### Step 6 — Start the FastAPI backend

```bash
uvicorn src.web_app.server:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at:

| URL | Description |
|---|---|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/ask` | Main chat endpoint (POST) |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc UI |

---

### Step 7 — (Optional) Start the React frontend

```bash
cd src/web_app/frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173`. It connects to the backend at `http://localhost:8000`.

---

### Step 8 — Verify with curl

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Finance Q&A
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is an ETF?"}'

# Tax education
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a Roth IRA?"}'

# Goal planning
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I plan for retirement?"}'
```

---

### Step 9 — Run the test suite

```bash
# From ai_finance_assistant/
pytest tests/ -v

# Run a quick smoke test of the multi-agent system
python test_system.py
```

---

### Troubleshooting (Local)

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Run `uvicorn` from the `ai_finance_assistant/` directory, not a subdirectory |
| `AuthenticationError: Incorrect API key` | Check `OPENAI_API_KEY` in `.env`; ensure no trailing spaces |
| `langgraph` not found | Run `pip install langgraph` or re-run `pip install -r requirements.txt` |
| Port 8000 already in use | `lsof -i :8000` to find the PID, then `kill <PID>`, or pass `--port 8001` |
| Frontend CORS error | Ensure FastAPI CORS middleware still has `allow_origins=["*"]` in `server.py` |

---

---

## Part 2: AWS Deployment

Three deployment options are described below, from simplest to most scalable.

| Option | Best for | Complexity |
|---|---|---|
| [Option A — ECS Fargate](#option-a--ecs-fargate-recommended) | Production, autoscaling | Medium |
| [Option B — EC2](#option-b--ec2) | Simple single-server deploy | Low |
| [Option C — Lambda + API Gateway](#option-c--lambda--api-gateway) | Low-traffic / serverless | Medium |

---

### Prerequisites (AWS)

- AWS account with permissions to create ECS, ECR, EC2, Lambda, Secrets Manager, and IAM resources
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured (`aws configure`)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- OpenAI API key stored in **AWS Secrets Manager** (see below)

---

### Store your API key in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name "ai-finance-assistant/OPENAI_API_KEY" \
  --secret-string "sk-proj-...your-key..."
```

Reference this secret in your task/function environment instead of hardcoding it.

---

### Create a `Dockerfile`

Add this file at `ai_finance_assistant/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start server
CMD ["uvicorn", "src.web_app.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and test locally first:

```bash
cd ai_finance_assistant
docker build -t ai-finance-assistant .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  ai-finance-assistant
curl http://localhost:8000/health   # should return {"status":"ok"}
```

---

### Option A — ECS Fargate (Recommended)

Fully managed containers — no servers to patch.

#### 1. Push image to Amazon ECR

```bash
# Create ECR repository (one-time)
aws ecr create-repository --repository-name ai-finance-assistant --region us-east-1

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS \
    --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag ai-finance-assistant:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-finance-assistant:latest

docker push \
  <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-finance-assistant:latest
```

#### 2. Create an ECS Cluster

```bash
aws ecs create-cluster --cluster-name ai-finance-assistant-cluster
```

#### 3. Create an ECS Task Definition

Save as `task-definition.json`:

```json
{
  "family": "ai-finance-assistant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "ai-finance-assistant",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-finance-assistant:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:ai-finance-assistant/OPENAI_API_KEY"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-finance-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register the task:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 4. Create a CloudWatch Log Group

```bash
aws logs create-log-group --log-group-name /ecs/ai-finance-assistant
```

#### 5. Create an ECS Service with a Load Balancer

```bash
# Create Application Load Balancer (or use console)
# Then create the ECS service:
aws ecs create-service \
  --cluster ai-finance-assistant-cluster \
  --service-name ai-finance-assistant-svc \
  --task-definition ai-finance-assistant \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=ai-finance-assistant,containerPort=8000"
```

#### 6. IAM permissions required

The **Task Execution Role** (`ecsTaskExecutionRole`) needs:
- `AmazonECSTaskExecutionRolePolicy` (managed)
- `secretsmanager:GetSecretValue` on your secret ARN

The **Task Role** (`ecsTaskRole`) needs:
- No extra permissions unless you add S3, RDS, or other AWS service calls

#### Architecture summary (ECS Fargate)

```
Internet
   │
   ▼
Application Load Balancer  (port 443 / 80)
   │
   ▼
ECS Fargate Task  (port 8000)
 └─ ai-finance-assistant container
      └─ reads OPENAI_API_KEY from Secrets Manager
      └─ logs to CloudWatch Logs
```

---

### Option B — EC2

Simple and inexpensive for low-traffic deployments.

#### 1. Launch an EC2 instance

- **AMI:** Amazon Linux 2023 or Ubuntu 22.04
- **Instance type:** `t3.small` or larger (1 vCPU / 2 GB RAM minimum)
- **Security group:** Allow TCP 22 (SSH) and TCP 8000 (or 80/443 via nginx)

#### 2. SSH in and set up the environment

```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>

# Install Python 3.11
sudo dnf install -y python3.11 python3.11-pip git        # Amazon Linux 2023
# sudo apt install -y python3.11 python3.11-venv git     # Ubuntu

# Clone repo
git clone https://github.com/mirfaizal/ai-finance-assistant-svc.git
cd ai-finance-assistant-svc/ai_finance_assistant

# Virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
echo "OPENAI_API_KEY=sk-proj-..." > .env
```

#### 3. Run with systemd (auto-restart on reboot)

Create `/etc/systemd/system/ai-finance.service`:

```ini
[Unit]
Description=AI Finance Assistant FastAPI
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/ai-finance-assistant-svc/ai_finance_assistant
EnvironmentFile=/home/ec2-user/ai-finance-assistant-svc/ai_finance_assistant/.env
ExecStart=/home/ec2-user/ai-finance-assistant-svc/ai_finance_assistant/.venv/bin/uvicorn \
          src.web_app.server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-finance
sudo systemctl start ai-finance
sudo systemctl status ai-finance
```

#### 4. (Optional) Add nginx as a reverse proxy

```bash
sudo dnf install -y nginx         # Amazon Linux 2023
# sudo apt install -y nginx       # Ubuntu
```

`/etc/nginx/conf.d/ai-finance.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo systemctl enable --now nginx
```

---

### Option C — Lambda + API Gateway

Best for very low traffic or event-driven architectures. Uses [Mangum](https://github.com/jordaneremieff/mangum) to wrap FastAPI as a Lambda handler.

#### 1. Install Mangum

```bash
pip install mangum
```

#### 2. Add Lambda handler to `server.py`

Add these lines at the bottom of `src/web_app/server.py`:

```python
# Lambda entry point (add to bottom of server.py)
from mangum import Mangum
handler = Mangum(app, lifespan="off")
```

#### 3. Package the Lambda function

```bash
cd ai_finance_assistant
pip install -r requirements.txt -t package/
cp -r src package/
cp config.yaml package/

cd package
zip -r ../deployment.zip .
```

#### 4. Create Lambda function

```bash
aws lambda create-function \
  --function-name ai-finance-assistant \
  --runtime python3.11 \
  --role arn:aws:iam::<ACCOUNT_ID>:role/lambda-execution-role \
  --handler src.web_app.server.handler \
  --zip-file fileb://deployment.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={OPENAI_API_KEY=sk-...}"
```

#### 5. Create API Gateway (HTTP API)

```bash
aws apigatewayv2 create-api \
  --name ai-finance-assistant-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:ai-finance-assistant
```

> **Note:** Lambda has a 29-second timeout enforced by API Gateway. If OpenAI responses exceed that, increase Lambda memory (which also increases CPU) or use ECS instead.

---

### AWS Resource Summary

| AWS Service | Purpose |
|---|---|
| **Amazon ECR** | Stores Docker container images |
| **Amazon ECS (Fargate)** | Runs containerised FastAPI app |
| **Application Load Balancer** | Distributes traffic, handles TLS termination |
| **AWS Secrets Manager** | Stores `OPENAI_API_KEY` securely |
| **Amazon CloudWatch Logs** | Application logs (`/ecs/ai-finance-assistant`) |
| **AWS IAM** | Task execution role, task role permissions |
| **Amazon S3** | (Future) Store RAG documents, financial datasets |
| **Amazon OpenSearch / pgvector** | (Future) Vector store for RAG |
| **AWS Lambda + API Gateway** | Serverless alternative to ECS |
| **AWS Systems Manager Param Store** | Alternative to Secrets Manager for config values |
| **Amazon Route 53** | Custom DNS for your load balancer / API |
| **AWS Certificate Manager** | Free TLS certificates for HTTPS |

---

### Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | **Yes** | OpenAI API key — platform.openai.com |
| `TAVILY_API_KEY` | No* | Tavily search key — tavily.com (* agents fall back to LLM-only without it) |
| `PINECONE_API_KEY` | No* | Pinecone API key — app.pinecone.io (* RAG disabled without it) |
| `PINECONE_INDEX` | No* | Name of your Pinecone index (default: `ai-finance-rag`) |
| `LANGCHAIN_TRACING_V2` | No | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No* | LangSmith API key (* required if tracing enabled) |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `ai-finance-assistant`) |
| `ALPHA_VANTAGE_API_KEY` | No | Alpha Vantage for raw market data (not currently wired in) |

### Pinecone Index Setup (one-time)

Before agents can retrieve RAG context, you must create the index and populate it:

```bash
# 1. Create a Serverless index in Pinecone console with:
#    - Name: ai-finance-rag  (matches PINECONE_INDEX)
#    - Dimension: 1536
#    - Metric: cosine

# 2. Populate the index with your financial documents:
python - <<'EOF'
from src.rag.pinecone_store import upsert_documents

upsert_documents([
    {
        "id": "etf-101",
        "text": "An ETF (Exchange-Traded Fund) is a type of investment fund ...",
        "metadata": {"source": "finance-basics", "agent": "finance_qa"}
    },
    {
        "id": "portfolio-diversification",
        "text": "Diversification reduces risk by spreading investments ...",
        "metadata": {"source": "portfolio-guide", "agent": "portfolio_analysis"}
    },
    # ... add as many chunks as you need
])
print("Upsert complete!")
EOF
```

---

### Security Best Practices

1. **Never hardcode API keys** — always use Secrets Manager or Parameter Store in AWS.
2. **Restrict CORS** — in `server.py`, change `allow_origins=["*"]` to your specific domain in production.
3. **Use HTTPS** — attach an ACM certificate to your ALB or CloudFront distribution.
4. **Restrict security groups** — only allow port 8000 from the ALB security group; never expose it to `0.0.0.0/0`.
5. **Rotate API keys** — schedule rotation in Secrets Manager.
6. **Enable CloudWatch alarms** — alert on 5xx error rates and Lambda/ECS invocation errors.
7. **Tag all resources** — use tags like `Project=ai-finance-assistant` and `Env=prod` for cost tracking.
