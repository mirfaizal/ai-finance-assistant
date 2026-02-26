# AWS EC2 Deployment Guide

Deploy the **AI Finance Assistant** on an EC2 instance using Docker Compose.

---

## Target Instance

| Item | Value |
|------|-------|
| **AMI ID** | `ami-0e3c3d18c4ad450a0` |
| **AMI Name** | Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.9 (Amazon Linux 2023) 20260214 |
| **Instance type (recommended)** | `g4dn.xlarge` (GPU) or `t3.large` / `t3.xlarge` (CPU-only) |
| **Storage** | 50 GB+ (gp3) |
| **Key pair** | `ag-key-pair.pem` |
| **SSH user** | `ec2-user` |
| **Public DNS** | `ec2-54-235-54-228.compute-1.amazonaws.com` |

### Required Security Group Rules

| Type | Protocol | Port | Source |
|------|----------|------|--------|
| SSH | TCP | 22 | Your IP (`x.x.x.x/32`) |
| HTTP (frontend) | TCP | 3000 | `0.0.0.0/0` |
| HTTP (backend API) | TCP | 8000 | `0.0.0.0/0` |

---

## Step 1 – Connect to the Instance

```bash
# Fix key permissions (only needed once)
chmod 400 ag-key-pair.pem

# SSH in
ssh -i "ag-key-pair.pem" ec2-user@ec2-54-235-54-228.compute-1.amazonaws.com
```

---

## Step 2 – Install Docker & Docker Compose

The Deep Learning AMI ships with Docker pre-installed. Verify and set up:

```bash
# ── Docker ────────────────────────────────────────────────────────────────────
docker --version          # should print Docker 25.x or newer

# If Docker is NOT installed:
# sudo dnf install -y docker
# sudo systemctl enable --now docker

# Add ec2-user to the docker group so you don't need sudo
sudo usermod -aG docker ec2-user
newgrp docker              # apply immediately without logout

# Verify
docker run --rm hello-world
```

```bash
# ── Docker Compose (v2 plugin) ────────────────────────────────────────────────
docker compose version    # should print Docker Compose version v2.x

# If Compose plugin is NOT present:
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

docker compose version
```

> **Note:** The AMI uses Amazon Linux 2023 (dnf/rpm), not Amazon Linux 2 (yum).

---

## Step 3 – Install Git & Clone the Repository

```bash
sudo dnf install -y git

git clone https://github.com/<YOUR_GITHUB_ORG>/ai-finance-assistant.git
cd ai-finance-assistant/ai_finance_assistant
```

> Replace `<YOUR_GITHUB_ORG>` with your actual GitHub org/user name.  
> If the repo is private, use a Personal Access Token or SSH key.

---

## Step 4 – Configure Environment Variables

The application reads secrets from a `.env` file at project root. **Never commit this file.**

```bash
# Copy the template
cp .env.example .env

# Edit with your real API keys
nano .env
```

Fill in **every required value**:

```dotenv
# ── Required ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-proj-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX=ai-finance-rag

# ── LangSmith Observability (optional) ───────────────────────────────────────
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your-langsmith-api-key-here
LANGCHAIN_PROJECT=ai-finance-assistant

# ── Alpha Vantage (optional real market data) ─────────────────────────────────
# ALPHA_VANTAGE_API_KEY=your-key-here
```

Save and exit: `Ctrl+X → Y → Enter` (nano).

---

## Step 5 – Build & Start the Application

```bash
# Build images and start all services in detached mode
docker compose up --build -d
```

Docker Compose will:
1. Build the **backend** image from `Dockerfile.backend`
2. Build the **frontend** image from `src/web_app/frontend/Dockerfile.frontend`
3. Start `ai-finance-backend` on port `8000`
4. Wait for the backend health check, then start `ai-finance-frontend` on port `3000`
5. Mount a named volume `db_data` for SQLite persistence

Expected output (abridged):

```
[+] Building ...
 ✔ backend   Built
 ✔ frontend  Built
[+] Running 3/3
 ✔ Network ai_finance_assistant_app-net  Created
 ✔ Container ai-finance-backend          Started
 ✔ Container ai-finance-frontend         Started
```

---

## Step 6 – Verify the Deployment

```bash
# Check container status (both should be healthy/running)
docker compose ps

# Tail logs (follow)
docker compose logs -f

# Tail a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Quick health check
curl http://localhost:8000/health
```

**Access from your browser:**

| Service | URL |
|---------|-----|
| Frontend | `http://ec2-54-235-54-228.compute-1.amazonaws.com:3000` |
| Backend API | `http://ec2-54-235-54-228.compute-1.amazonaws.com:8000` |
| API Docs (Swagger) | `http://ec2-54-235-54-228.compute-1.amazonaws.com:8000/docs` |

---

## Shut Down

```bash
# Stop and remove containers + network (keeps the db_data volume)
docker compose down

# Stop AND remove everything including the volume (⚠ deletes SQLite DB)
docker compose down -v
```

---

## Redeploy / Update

After pulling new code changes:

```bash
git pull

# Rebuild images and restart in one command
docker compose up --build -d
```

---

## Useful Commands

```bash
# Open a shell inside the running backend container
docker exec -it ai-finance-backend /bin/bash

# Open a shell inside the frontend container
docker exec -it ai-finance-frontend /bin/sh

# View Docker disk usage
docker system df

# Remove unused images/containers/volumes (free up disk space)
docker system prune -f

# Restart a single service without rebuilding
docker compose restart backend
```

---

## Persisted Data

The SQLite database is stored in a named Docker volume:

```bash
# Inspect the volume
docker volume inspect ai_finance_assistant_db_data

# Backup the database to the host
docker run --rm \
  -v ai_finance_assistant_db_data:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/db_backup_$(date +%Y%m%d).tar.gz /data
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `permission denied` running docker | Run `sudo usermod -aG docker ec2-user && newgrp docker` |
| `docker compose` not found | Install Compose v2 plugin (Step 2) |
| Frontend stuck waiting for backend | Check backend logs: `docker compose logs backend` |
| Port 3000 / 8000 not reachable | Verify Security Group inbound rules allow those ports |
| `OPENAI_API_KEY` missing error | Ensure `.env` is populated and saved before running compose |
| Out of disk space | Run `docker system prune -f` and check free disk with `df -h` |
