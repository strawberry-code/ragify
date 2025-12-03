# Ragify All-in-One Container
# Multi-stage build for Docker/Podman

# ============================================
# Stage 1: Builder - Install Python dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime - Final image
# ============================================
FROM python:3.12-slim

LABEL maintainer="Ragify"
LABEL description="All-in-one RAG documentation search with Ollama, Qdrant, and MCP"
LABEL version="1.0.0"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama - pinned to v0.11.0 to avoid embedding bugs in 0.12.x/0.13.x
# See: https://github.com/ollama/ollama/issues/13054
ENV OLLAMA_VERSION=0.11.0
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        OLLAMA_ARCH="arm64"; \
    else \
        OLLAMA_ARCH="amd64"; \
    fi && \
    curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-${OLLAMA_ARCH}.tgz" | \
    tar -xz -C /usr/local && \
    chmod +x /usr/local/bin/ollama

# Install Qdrant (standalone binary - architecture aware)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        QDRANT_ARCH="aarch64-unknown-linux-musl"; \
    else \
        QDRANT_ARCH="x86_64-unknown-linux-musl"; \
    fi && \
    curl -L "https://github.com/qdrant/qdrant/releases/download/v1.12.4/qdrant-${QDRANT_ARCH}.tar.gz" | \
    tar xz -C /usr/local/bin

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY lib/ ./lib/
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY src/ ./src/
COPY ragify.py .
COPY config.yaml .
COPY docker/ ./docker/

# Make scripts executable
RUN chmod +x /app/docker/*.sh

# Pre-pull default Ollama model (makes container larger but faster startup)
# This runs ollama serve temporarily to pull the model
RUN ollama serve & \
    sleep 5 && \
    ollama pull nomic-embed-text && \
    pkill ollama || true

# Create data directory for Qdrant
RUN mkdir -p /data/qdrant

# Environment variables with defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # API Configuration
    API_PORT=8080 \
    MCP_PORT=6666 \
    # Ollama (internal)
    OLLAMA_URL=http://localhost:11434 \
    OLLAMA_MODEL=nomic-embed-text \
    # Qdrant (internal)
    QDRANT_URL=http://localhost:6333 \
    QDRANT_PATH=/data/qdrant \
    # Auth (must be provided)
    AUTH_CONFIG="" \
    GITHUB_CLIENT_ID="" \
    GITHUB_CLIENT_SECRET="" \
    BASE_URL=http://localhost:8080

# Volumes
VOLUME ["/data"]

# Expose ports
EXPOSE 8080 6666

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/docker/healthcheck.sh

# Use tini as init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run entrypoint script
CMD ["/app/docker/entrypoint.sh"]
