# ==============================================================================
# Multi-Stage Production Dockerfile for CampusLink 2.0
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install system build dependencies required for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# STAGE 2: Hardened Runtime
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Set environment paths and python unbuffered mode
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create unprivileged application security user
RUN groupadd -g 10001 campuslink && \
    useradd -u 10001 -g campuslink -s /bin/bash -m campuslink

# Copy application source code with unprivileged ownership
COPY --chown=campuslink:campuslink . /app

# Drop root privileges
USER campuslink

EXPOSE 5000

# Production WSGI server execution
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
