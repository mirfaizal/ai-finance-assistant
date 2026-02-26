# Docker Compose Instructions

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | ≥ 24.x | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | ≥ 2.x (bundled with Docker Desktop) | included |

---

## 1. Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
OPENAI_API_KEY=sk-proj-...        # Required
TAVILY_API_KEY=tvly-...           # Required
PINECONE_API_KEY=...              # Required
PINECONE_INDEX=ai-finance-rag     # Required

LANGCHAIN_TRACING_V2=false        # Optional (set true to enable LangSmith)
LANGCHAIN_API_KEY=...             # Optional
LANGCHAIN_PROJECT=ai-finance-assistant
```

> ⚠️ **Never commit `.env` to git** — it is already in `.gitignore`.

---

## 2. Build and Start

```bash
docker-compose up --build -d
```

This will:
1. Build the **backend** image (Python / FastAPI)
2. Build the **frontend** image (React → nginx)
3. Start both containers
4. Create a named volume `db_data` for the SQLite database

---

## 3. Verify Everything Is Running

```bash
# Check containers are up
docker-compose ps

# Check backend health
curl http://localhost:8000/health
# → {"status": "ok"}

# Check frontend is serving
curl -I http://localhost:3000
# → HTTP/1.1 200 OK

# Test the nginx proxy (frontend → backend)
curl http://localhost:3000/api/health
# → {"status": "ok"}
```

Open the app: **http://localhost:3000**

---

## 4. Common Commands

| Action | Command |
|--------|---------|
| Start (already built) | `docker-compose up -d` |
| Rebuild and start | `docker-compose up --build -d` |
| Stop containers | `docker-compose stop` |
| Stop and remove containers | `docker-compose down` |
| Stop + wipe database | `docker-compose down -v` |
| View live logs | `docker-compose logs -f` |
| Backend logs only | `docker-compose logs -f backend` |
| Frontend logs only | `docker-compose logs -f frontend` |
| Open a shell in backend | `docker-compose exec backend /bin/bash` |

---

## 5. Ports

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3000 | React app served by nginx |
| Backend API | http://localhost:8000 | FastAPI / uvicorn (direct) |
| Backend via nginx | http://localhost:3000/api/ | Proxied through the frontend |
| API Docs (Swagger) | http://localhost:8000/docs | FastAPI auto-generated |

---

## 6. Data Persistence

SQLite data (`conversations.db`) lives in a Docker named volume:

```bash
# List volumes
docker volume ls | grep db_data

# Inspect the volume path
docker volume inspect ai_finance_assistant_db_data

# Back up the database
docker-compose exec backend sqlite3 /app/data/conversations.db .dump > backup.sql
```

The data **survives** `docker-compose down`.  
To **wipe** it: `docker-compose down -v`

---

## 7. Troubleshooting

**Backend fails to start / crashes**
```bash
docker-compose logs backend
# Check for missing API keys or import errors
```

**Frontend shows "Backend offline"**
```bash
# The frontend health-checks the backend on load.
# Make sure the backend is healthy first:
docker-compose ps
docker-compose logs backend
```

**Port already in use**
```bash
# Change the host port in docker-compose.yml, e.g.:
#   ports: ["8001:8000"]   ← backend
#   ports: ["3001:80"]     ← frontend
```

**Rebuild after code changes**
```bash
docker-compose up --build -d
```

---

## 8. AWS Deployment

See [`aws/README.md`](aws/README.md) for deploying to ECS Fargate.  
Once set up, deploy with a single command:

```bash
./aws/deploy.sh
```
