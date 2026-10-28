# Multi-stage Dockerfile for MockMate (Backend & Frontend)
FROM python:3.13-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code (excluding entries in .dockerignore)
COPY . .

# ----------------------------------------------------
# Target: Backend service (FastAPI)
# ----------------------------------------------------
FROM base AS backend

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ----------------------------------------------------
# Target: Frontend service (Streamlit)
# ----------------------------------------------------
FROM base AS frontend

EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
