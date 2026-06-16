# ── Stage 1: base image ───────────────────────────────────────────────────────
FROM python:3.11-slim

# Metadata (shown on Docker Hub)
LABEL maintainer="your-dockerhub-username"
LABEL description="Bank Onboarding Agent Marketplace — KYC, Credit, Fraud agents via REST API"
LABEL version="1.0.0"

# ── System setup ──────────────────────────────────────────────────────────────
WORKDIR /app

# Copy and install dependencies first (Docker layer caching — faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# ── Runtime config ────────────────────────────────────────────────────────────
# Port 8000 is where FastAPI listens inside the container
EXPOSE 8000

# Healthcheck — Docker will mark container unhealthy if /health fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the API server
# --host 0.0.0.0  → accept connections from outside the container
# --port 8000     → internal port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]