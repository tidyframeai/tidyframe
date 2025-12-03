# ================================
# Multi-Stage Production Dockerfile - Backend
# TidyFrame.ai - Optimized for Security & Performance
# ================================

# ================================
# Stage 1: Build Dependencies
# ================================
FROM python:3.11-slim-bookworm AS dependencies

# Build args for cache invalidation
ARG BUILDKIT_INLINE_CACHE=1

# Set environment variables for build stage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install build dependencies (will be removed in final stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ================================
# Stage 2: Production Runtime
# ================================
FROM python:3.11-slim-bookworm AS production

# Build metadata labels
LABEL maintainer="TidyFrame Team" \
      version="1.0.0" \
      description="TidyFrame.ai Backend Production Container" \
      org.opencontainers.image.source="https://github.com/tidyframe/backend"

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# Install runtime dependencies only (minimal footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Copy virtual environment from dependencies stage
COPY --from=dependencies /opt/venv /opt/venv

# Create non-root user with minimal privileges
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /sbin/nologin \
    -c "Application User" appuser

# Set work directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser alembic.ini .
# Copy .env file if it exists (for development)
# COPY --chown=appuser:appuser .env* ./

# Copy frontend static files (built from frontend/dist)
# These files are copied during build, not via volume mount
COPY --chown=appuser:appuser app/static/ ./app/static/

# Create directories with proper permissions
RUN mkdir -p /app/uploads /app/results /app/logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 750 /app/uploads /app/results /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Add comprehensive health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production-optimized command with Gunicorn
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "90", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]