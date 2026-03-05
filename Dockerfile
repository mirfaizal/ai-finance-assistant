# ── Hugging Face Spaces — Single-container Dockerfile ─────────────────────────
# Builds the React/Vite frontend and bundles it with the FastAPI backend
# into one image served by nginx (port 7860) + uvicorn (port 8000 internally).
#
# HF Spaces requirements:
#   • App must be accessible on port 7860 (set via EXPOSE + nginx listen)
#   • Secrets (API keys) are injected as Space secrets in the HF UI
#
# Build context: project root (ai_finance_assistant/)

# ── Stage 1: Build React / Vite frontend ─────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies (cached layer)
COPY src/web_app/frontend/package.json src/web_app/frontend/package-lock.json ./
RUN npm ci --prefer-offline

# Copy all frontend source files
COPY src/web_app/frontend/ .

# Build — VITE_API_BASE_URL="" means all /api/* calls use the nginx proxy
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build


# ── Stage 2: Python runtime + nginx + supervisord ─────────────────────────────
FROM python:3.12-slim AS runtime

# Keeps Python from generating .pyc files; enables unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENV AUTH0_DOMAIN=${AUTH0_DOMAIN}
ENV AUTH0_AUDIENCE=${AUTH0_AUDIENCE}

WORKDIR /app

# Install system packages: nginx (web server), supervisor (process manager),
# curl (health-check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
COPY src/        ./src/
COPY config.yaml .
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# SQLite database directory (ephemeral within the Space's lifetime)
RUN mkdir -p /app/data

# ── Nginx configuration ───────────────────────────────────────────────────────
# Remove the default site and install our HF-specific config
RUN rm -f /etc/nginx/sites-enabled/default \
    /etc/nginx/conf.d/default.conf
COPY deploy/nginx_hf.conf /etc/nginx/conf.d/app.conf

# ── Copy compiled React app from Stage 1 ─────────────────────────────────────
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# ── Supervisord configuration ─────────────────────────────────────────────────
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ── Permissions ───────────────────────────────────────────────────────────────
# Allow nginx to write its pid and cache files
RUN mkdir -p /var/cache/nginx /var/run \
    && chown -R root:root /var/cache/nginx

# ── Port ─────────────────────────────────────────────────────────────────────
# HF Spaces routes external traffic to this port
EXPOSE 7860

# ── Health-check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
# Run the entrypoint script which injects runtime environment variables into
# index.html before starting supervisord to manage nginx and uvicorn.
CMD ["/app/entrypoint.sh"]
