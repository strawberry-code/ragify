#!/bin/bash
# Health check script for Docker HEALTHCHECK

API_PORT="${API_PORT:-8080}"

# Check API health endpoint
response=$(curl -sf "http://localhost:${API_PORT}/health" 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "API health check failed: cannot connect"
    exit 1
fi

# Parse JSON response
status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$status" = "healthy" ]; then
    exit 0
else
    echo "API health check failed: status=$status"
    exit 1
fi
