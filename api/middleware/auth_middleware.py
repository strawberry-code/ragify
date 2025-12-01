"""
Authentication middleware for FastAPI.

Protects routes based on authentication status and configuration.
"""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.auth import is_auth_enabled, get_current_user


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
    "/favicon.ico"
}

# Path prefixes that don't require authentication
PUBLIC_PREFIXES = (
    "/static/",
    "/auth/",
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

        # Check authentication
        user = get_current_user(request)

        if not user:
            # API routes return 401
            if path.startswith("/api/") or path.startswith("/mcp/"):
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            # Browser routes redirect to login
            return RedirectResponse(url="/auth/login", status_code=302)

        # User is authenticated, continue
        return await call_next(request)


def require_auth(request: Request) -> dict:
    """
    Dependency to require authentication.

    Use as a FastAPI dependency on routes that need auth.

    Args:
        request: FastAPI request

    Returns:
        dict: User information

    Raises:
        HTTPException: If not authenticated
    """
    if not is_auth_enabled():
        return {"username": "anonymous", "authenticated": False}

    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return user
