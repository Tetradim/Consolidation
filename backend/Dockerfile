# ============================================================
# Trading Bot Backend Dockerfile
# Multi-stage build for optimized production image
# ============================================================

# --------------------------------------------------------
# Stage 1: Base Python
# --------------------------------------------------------
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    htop \
    net-tools \
    iputils-ping \
    dnsutils \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r tradebot && useradd -r -g tradebot tradebot

# Set work directory
WORKDIR /app

# --------------------------------------------------------
# Stage 2: Python dependencies
# --------------------------------------------------------
FROM base as dependencies

# Copy requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# --------------------------------------------------------
# Stage 3: Application
# --------------------------------------------------------
FROM base as production

# Copy Python dependencies from builder
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ /app/

# Create data directories
RUN mkdir -p /data /logs && chown -R tradebot:tradebot /app /data /logs

# Switch to non-root user
USER tradebot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "-m", "backend"]

# --------------------------------------------------------
# Stage 4: Development (optional)
# --------------------------------------------------------
FROM base as development

# Install development dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
RUN pip install debugpy black flake8 isort pytest pytest-asyncio pytest-cov

# Copy source code
COPY backend/ /app/

WORKDIR /app

# Run in debug mode
CMD ["python", "-m", "backend"]