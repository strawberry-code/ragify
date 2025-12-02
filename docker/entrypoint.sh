#!/bin/bash
set -e

echo "========================================"
echo "  Ragify Container Starting"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate required configuration
validate_config() {
    log_info "Validating configuration..."

    # Check AUTH_CONFIG if authentication is enabled
    if [ -n "$GITHUB_CLIENT_ID" ] && [ -n "$GITHUB_CLIENT_SECRET" ]; then
        if [ -z "$AUTH_CONFIG" ]; then
            log_error "AUTH_CONFIG is required when GitHub OAuth is configured"
            exit 1
        fi

        if [ ! -f "$AUTH_CONFIG" ]; then
            log_error "AUTH_CONFIG file not found: $AUTH_CONFIG"
            exit 1
        fi

        # Check if users.yaml has at least one user
        if ! grep -q "username:" "$AUTH_CONFIG" 2>/dev/null; then
            log_error "AUTH_CONFIG must contain at least one authorized user"
            exit 1
        fi

        log_info "Authentication configured with $(grep -c 'username:' "$AUTH_CONFIG") authorized users"
    else
        log_warn "GitHub OAuth not configured - authentication disabled"
    fi
}

# Start Qdrant
start_qdrant() {
    log_info "Starting Qdrant..."

    # Create data directory if needed
    mkdir -p "${QDRANT_PATH:-/data/qdrant}"

    # Set Qdrant environment variables
    export QDRANT__STORAGE__STORAGE_PATH="${QDRANT_PATH:-/data/qdrant}"
    export QDRANT__SERVICE__TELEMETRY_DISABLED=true
    export QDRANT__SERVICE__STATIC_CONTENT_DIR=""

    # Start Qdrant in background with config
    qdrant --config-path /app/docker/qdrant_config.yaml 2>&1 | grep -v "Config file not found" &
    QDRANT_PID=$!

    # Wait for Qdrant to be ready
    log_info "Waiting for Qdrant to be ready..."
    for i in {1..30}; do
        if curl -sf http://localhost:6333/collections > /dev/null 2>&1; then
            log_info "Qdrant is ready (PID: $QDRANT_PID)"
            return 0
        fi
        sleep 1
    done

    log_error "Qdrant failed to start within 30 seconds"
    exit 1
}

# Start Ollama
start_ollama() {
    log_info "Starting Ollama..."

    # Start Ollama in background
    ollama serve &
    OLLAMA_PID=$!

    # Wait for Ollama to be ready
    log_info "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
            log_info "Ollama is ready (PID: $OLLAMA_PID)"
            break
        fi
        sleep 1
    done

    # Check if model is available, pull if needed
    MODEL="${OLLAMA_MODEL:-nomic-embed-text}"
    log_info "Checking for model: $MODEL"

    if ! ollama list | grep -q "$MODEL"; then
        log_info "Pulling model $MODEL (this may take a while)..."
        ollama pull "$MODEL"
    fi

    log_info "Model $MODEL is available"
}

# Start FastAPI
start_api() {
    log_info "Starting FastAPI API server..."

    # Determine SSL configuration
    SSL_ARGS=""
    if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ] && [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
        log_info "HTTPS enabled with certificates"
        SSL_ARGS="--ssl-certfile=$SSL_CERT --ssl-keyfile=$SSL_KEY"
    fi

    # Start uvicorn
    cd /app
    exec uvicorn api.main:app \
        --host 0.0.0.0 \
        --port "${API_PORT:-8080}" \
        --workers 1 \
        --log-level info \
        $SSL_ARGS
}

# Cleanup on exit
cleanup() {
    log_info "Shutting down..."
    [ -n "$QDRANT_PID" ] && kill $QDRANT_PID 2>/dev/null || true
    [ -n "$OLLAMA_PID" ] && kill $OLLAMA_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Main
main() {
    validate_config
    start_qdrant
    start_ollama
    start_api
}

main
