"""
GitHub OAuth authentication module.

Implements OAuth 2.0 flow with GitHub and validates users against
a YAML whitelist configuration.
"""

import os
import secrets
from pathlib import Path
from typing import Optional

import yaml
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

router = APIRouter()

# Configuration
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
AUTH_CONFIG = os.getenv('AUTH_CONFIG', '')
SESSION_SECRET = os.getenv('SESSION_SECRET', secrets.token_hex(32))
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8080')

# GitHub OAuth URLs
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Session serializer
serializer = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE = "ragify_session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


def load_authorized_users() -> list[str]:
    """
    Load authorized usernames from YAML config.

    Returns:
        list: List of authorized GitHub usernames
    """
    if not AUTH_CONFIG:
        return []

    config_path = Path(AUTH_CONFIG)
    if not config_path.exists():
        return []

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)

        if not data or 'authorized_users' not in data:
            return []

        users = data['authorized_users']
        return [u.get('username', u) if isinstance(u, dict) else u for u in users]
    except Exception:
        return []


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET and AUTH_CONFIG)


def create_session(username: str, access_token: str) -> str:
    """
    Create a signed session token.

    Args:
        username: GitHub username
        access_token: GitHub access token

    Returns:
        str: Signed session token
    """
    return serializer.dumps({
        "username": username,
        "access_token": access_token
    })


def verify_session(token: str) -> Optional[dict]:
    """
    Verify and decode session token.

    Args:
        token: Session token

    Returns:
        dict: Session data or None if invalid
    """
    try:
        return serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request: Request) -> Optional[dict]:
    """
    Get current user from request session.

    Args:
        request: FastAPI request

    Returns:
        dict: User info or None if not authenticated
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    session = verify_session(token)
    if not session:
        return None

    return session


@router.get("/login")
async def login(request: Request):
    """
    Redirect to GitHub OAuth authorization.

    Returns:
        RedirectResponse: Redirect to GitHub login
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=503,
            detail="Authentication not configured. Set GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, and AUTH_CONFIG."
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in cookie (short-lived)
    redirect_uri = f"{BASE_URL}/oauth/github-callback"
    auth_url = (
        f"{GITHUB_AUTH_URL}?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=read:user&"
        f"state={state}"
    )

    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,  # 10 minutes
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax"
    )
    return response


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """
    Handle GitHub OAuth callback.

    Args:
        code: Authorization code from GitHub
        state: State parameter for CSRF verification
        error: Error message if authorization failed

    Returns:
        RedirectResponse: Redirect to dashboard or login page
    """
    if error:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")

    # Verify state
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{BASE_URL}/auth/callback"
            },
            headers={"Accept": "application/json"}
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Get user info
        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()
        username = user_data.get("login")

        if not username:
            raise HTTPException(status_code=400, detail="Could not determine username")

    # Check if user is authorized
    authorized_users = load_authorized_users()
    if authorized_users and username not in authorized_users:
        raise HTTPException(
            status_code=403,
            detail=f"User '{username}' is not authorized. Contact administrator."
        )

    # Create session
    session_token = create_session(username, access_token)

    # Redirect to dashboard with session cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax"
    )
    response.delete_cookie("oauth_state")

    return response


@router.get("/logout")
async def logout():
    """
    Logout and clear session.

    Returns:
        RedirectResponse: Redirect to home page
    """
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/me")
async def get_user_info(request: Request):
    """
    Get current user information.

    Returns:
        dict: User information or error
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "username": user["username"],
        "authenticated": True
    }


@router.get("/status")
async def auth_status(request: Request):
    """
    Get authentication status.

    Returns:
        dict: Auth configuration status
    """
    user = get_current_user(request)

    return {
        "enabled": is_auth_enabled(),
        "authenticated": user is not None,
        "username": user["username"] if user else None,
        "config": {
            "github_configured": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
            "users_config": bool(AUTH_CONFIG),
            "users_count": len(load_authorized_users())
        }
    }
