"""
Authentication middleware for FastAPI.

Protects routes based on authentication status and configuration.
Supports session cookies, Bearer tokens for OAuth 2.0, and static API keys.
"""

import os

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.auth import is_auth_enabled, get_current_user
from api.oauth import validate_bearer_token

# Static API key for MCP clients (optional)
MCP_API_KEY = os.getenv("MCP_API_KEY")


def validate_api_key(api_key: str) -> dict | None:
    """
    Validate static API key for MCP clients.

    Args:
        api_key: The API key to validate

    Returns:
        dict: User info if valid, None otherwise
    """
    if not MCP_API_KEY:
        return None

    if api_key == MCP_API_KEY:
        return {
            "username": "mcp-client",
            "authenticated": True,
            "auth_type": "api_key"
        }

    return None


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/metrics",
    "/auth/login",
    "/auth/callback",
    "/auth/status",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/static",
    "/favicon.ico",
    "/register",  # OAuth dynamic client registration
}

# Path prefixes that don't require authentication
PUBLIC_PREFIXES = (
    "/static/",
    "/auth/",
    "/.well-known/",  # OAuth discovery endpoints
    "/oauth/",  # OAuth endpoints (authorize, token, register)
)


def is_public_path(path: str) -> bool:
    """
    Check if path is public (doesn't require auth).

    Args:
        path: Request path

    Returns:
        bool: True if path is public
    """
    if path in PUBLIC_PATHS:
        return True

    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication on protected routes.

    If AUTH_CONFIG is set, all non-public routes require authentication.
    Users are redirected to /auth/login if not authenticated.
    API routes return 401 instead of redirect.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth check for public paths
        if is_public_path(path):
            return await call_next(request)

        # Skip if auth not enabled
        if not is_auth_enabled():
            return await call_next(request)

        # Check for X-API-Key header first (for MCP clients with static key)
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            api_key_data = validate_api_key(api_key)
            if api_key_data:
                request.state.user = api_key_data
                return await call_next(request)

        # Check for Bearer token (for MCP/API clients with OAuth)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            # First try as static API key
            api_key_data = validate_api_key(token)
            if api_key_data:
                request.state.user = api_key_data
                return await call_next(request)
            # Then try as OAuth token
            token_data = validate_bearer_token(token)
            if token_data:
                # Token is valid, continue
                request.state.user = token_data
                return await call_next(request)

        # Check session cookie (for browser users)
        user = get_current_user(request)

        if not user:
            # API routes return 401 JSON response
            if path.startswith("/api/") or path.startswith("/mcp/"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"}
                )

            # Browser routes redirect to login
            return RedirectResponse(url="/auth/login", status_code=302)

        # User is authenticated, continue
        request.state.user = user
        return await call_next(request)


def require_auth(request: Request) -> dict:
    """
    Dependency to require authentication.

    Use as a FastAPI dependency on routes that need auth.
    Supports both session cookies and Bearer tokens.

    Args:
        request: FastAPI request

    Returns:
        dict: User information

    Raises:
        HTTPException: If not authenticated
    """
    if not is_auth_enabled():
        return {"username": "anonymous", "authenticated": False}

    # Check for X-API-Key header first
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        api_key_data = validate_api_key(api_key)
        if api_key_data:
            return api_key_data

    # Check for Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # First try as static API key
        api_key_data = validate_api_key(token)
        if api_key_data:
            return api_key_data
        # Then try as OAuth token
        token_data = validate_bearer_token(token)
        if token_data:
            return {
                "username": token_data.get("username"),
                "authenticated": True,
                "auth_type": "bearer"
            }

    # Check session cookie
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return {**user, "auth_type": "session"}
