"""System API routes."""

import os
import platform
from datetime import datetime

from fastapi import APIRouter
import requests

router = APIRouter()

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Track start time
START_TIME = datetime.utcnow()


@router.get("/status", tags=["System"])
async def system_status():
    """
    Detailed system status.

    Returns:
        dict: Complete system information and component status
    """
    # Check Ollama
    ollama_status = {"status": "error", "models": []}
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            ollama_status = {
                "status": "ok",
                "url": OLLAMA_URL,
                "models": [m["name"] for m in data.get("models", [])]
            }
    except Exception as e:
        ollama_status["error"] = str(e)

    # Check Qdrant
    qdrant_status = {"status": "error", "collections": []}
    try:
        headers = {}
        if QDRANT_API_KEY:
            headers['api-key'] = QDRANT_API_KEY

        resp = requests.get(f"{QDRANT_URL}/collections", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            collections = data.get("result", {}).get("collections", [])
            qdrant_status = {
                "status": "ok",
                "url": QDRANT_URL,
                "collections": [c["name"] for c in collections],
                "authenticated": bool(QDRANT_API_KEY)
            }
    except Exception as e:
        qdrant_status["error"] = str(e)

    # Calculate uptime
    uptime = datetime.utcnow() - START_TIME
    uptime_seconds = int(uptime.total_seconds())

    return {
        "status": "ok" if ollama_status["status"] == "ok" and qdrant_status["status"] == "ok" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "components": {
            "ollama": ollama_status,
            "qdrant": qdrant_status
        },
        "config": {
            "api_port": os.getenv('API_PORT', '8080'),
            "mcp_port": os.getenv('MCP_PORT', '6666'),
            "ollama_model": os.getenv('OLLAMA_MODEL', 'nomic-embed-text'),
            "auth_enabled": bool(os.getenv('AUTH_CONFIG'))
        }
    }


@router.get("/api/info", tags=["System"])
async def api_info():
    """
    API information.

    Returns:
        dict: API version and endpoints info
    """
    return {
        "name": "Ragify API",
        "version": "1.0.0",
        "description": "REST API for RAG documentation indexing and search",
        "docs": "/api/docs",
        "endpoints": {
            "collections": "/api/collections",
            "upload": "/api/upload",
            "search": "/api/search",
            "jobs": "/api/jobs",
            "health": "/health",
            "metrics": "/metrics",
            "status": "/status"
        }
    }
