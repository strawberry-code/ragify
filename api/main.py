"""
Ragify API - FastAPI application for container deployment.

Provides REST API for ragify operations, MCP SSE transport, and serves the frontend SPA.
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Configure logging early, before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Override any existing configuration
)
# Disable buffering for real-time logs
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Silence verbose HTTP client logs (httpx logs every single request)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# Silence Tika startup warnings ("Failed to see startup log message; retrying...")
logging.getLogger("tika").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from api.routes import collections, upload, search, system, mcp
from api import auth, oauth
from api.middleware.auth_middleware import AuthMiddleware

# Metrics
REQUEST_COUNT = Counter(
    'ragify_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'ragify_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

# App configuration
API_PORT = int(os.getenv('API_PORT', '8080'))
FRONTEND_DIR = Path(__file__).parent.parent / 'frontend'


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Ragify API starting on port {API_PORT}")
    yield
    # Shutdown
    logger.info("Ragify API shutting down")


app = FastAPI(
    title="Ragify API",
    description="REST API for RAG documentation indexing and search",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    start_time = time.time()
    response = await call_next(request)

    # Record metrics
    latency = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

    return response


# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(oauth.router, tags=["OAuth"])  # OAuth at root for .well-known paths
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(system.router, tags=["System"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])


# Health check endpoint (no auth required)
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes.

    Returns:
        dict: Health status with component checks
    """
    import requests

    ollama_ok = False
    qdrant_ok = False

    # Check Ollama
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        ollama_ok = resp.status_code == 200
    except Exception:
        pass

    # Check Qdrant
    qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    try:
        headers = {}
        if qdrant_api_key:
            headers['api-key'] = qdrant_api_key
        resp = requests.get(f"{qdrant_url}/collections", headers=headers, timeout=5)
        qdrant_ok = resp.status_code == 200
    except Exception:
        pass

    healthy = ollama_ok and qdrant_ok
    status_code = 200 if healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "unhealthy",
            "components": {
                "ollama": "ok" if ollama_ok else "error",
                "qdrant": "ok" if qdrant_ok else "error"
            }
        }
    )


# Prometheus metrics endpoint
@app.get("/metrics", tags=["System"])
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        Response: Prometheus-formatted metrics
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Serve frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


# Serve favicon
@app.get("/favicon.ico", tags=["Frontend"], include_in_schema=False)
@app.get("/favicon.svg", tags=["Frontend"], include_in_schema=False)
async def serve_favicon():
    """Serve favicon."""
    favicon_path = FRONTEND_DIR / "static" / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/svg+xml")
    return Response(status_code=204)


# Serve apple touch icons (return 204 No Content to suppress 404)
@app.get("/apple-touch-icon.png", tags=["Frontend"], include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", tags=["Frontend"], include_in_schema=False)
async def serve_apple_icon():
    """Serve apple touch icon (or empty response)."""
    return Response(status_code=204)


# Serve frontend SPA (catch-all for client-side routing)
@app.get("/", tags=["Frontend"])
@app.get("/dashboard", tags=["Frontend"])
@app.get("/collections", tags=["Frontend"])
@app.get("/upload", tags=["Frontend"])
@app.get("/search", tags=["Frontend"])
@app.get("/settings", tags=["Frontend"])
async def serve_frontend():
    """Serve the frontend SPA."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=404,
        content={"error": "Frontend not found"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=False
    )
