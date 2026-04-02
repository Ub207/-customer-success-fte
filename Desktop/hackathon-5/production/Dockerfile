FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so this layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Non-root user ─────────────────────────────────────────────────────────────
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# ── Runtime defaults ──────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_FORMAT=json \
    LOG_LEVEL=INFO

EXPOSE 8000

# Default: FastAPI API server.
# Override CMD in docker-compose for worker and reporter processes.
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
