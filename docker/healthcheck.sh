#!/bin/bash
# Health check script for Docker HEALTHCHECK
# Verifica: API, Ollama, Qdrant, Tika

API_PORT="${API_PORT:-8080}"

# Check API health endpoint (include Ollama + Qdrant check)
response=$(curl -sf "http://localhost:${API_PORT}/health" 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "API health check failed: cannot connect"
    exit 1
fi

# Parse JSON response
status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$status" != "healthy" ]; then
    echo "API health check failed: status=$status"
    exit 1
fi

# Check Tika server
tika_response=$(curl -sf "http://localhost:9998/version" 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Tika health check failed: cannot connect to port 9998"
    exit 1
fi

# All checks passed
exit 0
