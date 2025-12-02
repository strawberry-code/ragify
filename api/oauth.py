"""
OAuth 2.0 Authorization Server for MCP.

Implements RFC 8414 (OAuth 2.0 Authorization Server Metadata),
RFC 7591 (Dynamic Client Registration), and Authorization Code flow
with PKCE for MCP clients like Claude Code.
"""

import os
import secrets
import hashlib
import base64
import time
from typing import Optional
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter()

# Configuration
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
AUTH_CONFIG = os.getenv('AUTH_CONFIG', '')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8080')
TOKEN_SECRET = os.getenv('TOKEN_SECRET', secrets.token_hex(32))

# GitHub OAuth URLs
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Token expiry
ACCESS_TOKEN_EXPIRY = 3600 * 24  # 24 hours
REFRESH_TOKEN_EXPIRY = 3600 * 24 * 30  # 30 days

# In-memory stores (use Redis in production)
registered_clients: dict[str, dict] = {}
auth_codes: dict[str, dict] = {}  # code -> {client_id, user, code_challenge, expires}
access_tokens: dict[str, dict] = {}  # token -> {client_id, user, expires}
refresh_tokens: dict[str, dict] = {}  # token -> {client_id, user, expires}
pending_auth: dict[str, dict] = {}  # state -> {client_id, redirect_uri, code_challenge, code_challenge_method}


def is_oauth_enabled() -> bool:
    """Check if OAuth is properly configured."""
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code challenge."""
    if method == "plain":
        return code_verifier == code_challenge
    elif method == "S256":
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
        return computed == code_challenge
    return False


# OAuth 2.0 Metadata (RFC 8414)
@router.get("/.well-known/oauth-authorization-server")
@router.get("/.well-known/oauth-authorization-server/{path:path}")
async def oauth_metadata(request: Request, path: str = ""):
    """
    OAuth 2.0 Authorization Server Metadata.

    RFC 8414 compliant metadata endpoint.
    """
    issuer = BASE_URL

    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "service_documentation": f"{issuer}/api/docs"
    }


# Also serve at root .well-known for compatibility
@router.get("/.well-known/openid-configuration")
@router.get("/.well-known/openid-configuration/{path:path}")
async def openid_metadata(request: Request, path: str = ""):
    """OpenID Connect Discovery (returns OAuth metadata)."""
    return await oauth_metadata(request, path)


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/{path:path}")
async def protected_resource_metadata(request: Request, path: str = ""):
    """OAuth 2.0 Protected Resource Metadata."""
    return {
        "resource": BASE_URL,
        "authorization_servers": [BASE_URL],
        "scopes_supported": ["mcp:read", "mcp:write"]
    }


# Dynamic Client Registration (RFC 7591)
class ClientRegistration(BaseModel):
    """Client registration request."""
    client_name: str = "MCP Client"
    redirect_uris: list[str] = []
    grant_types: list[str] = ["authorization_code", "refresh_token"]
    response_types: list[str] = ["code"]
    scope: str = "mcp:read mcp:write"


@router.post("/oauth/register")
@router.post("/register")
async def register_client(request: Request):
    """
    Dynamic Client Registration.

    RFC 7591 compliant client registration endpoint.
    Allows MCP clients to register dynamically.
    """
    try:
        body = await request.json()
    except:
        body = {}

    client_id = generate_token()
    client_secret = generate_token()

    client = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": body.get("client_name", "MCP Client"),
        "redirect_uris": body.get("redirect_uris", []),
        "grant_types": body.get("grant_types", ["authorization_code", "refresh_token"]),
        "response_types": body.get("response_types", ["code"]),
        "scope": body.get("scope", "mcp:read mcp:write"),
        "created_at": datetime.utcnow().isoformat()
    }

    registered_clients[client_id] = client

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": client["client_name"],
        "redirect_uris": client["redirect_uris"],
        "grant_types": client["grant_types"],
        "response_types": client["response_types"],
        "scope": client["scope"]
    }


# Authorization Endpoint
@router.get("/oauth/authorize")
async def authorize(
    request: Request,
    response_type: str = "code",
    client_id: str = "",
    redirect_uri: str = "",
    scope: str = "mcp:read",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256"
):
    """
    OAuth 2.0 Authorization Endpoint.

    Initiates the authorization flow by redirecting to GitHub.
    """
    if not is_oauth_enabled():
        raise HTTPException(
            status_code=503,
            detail="OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
        )

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only 'code' response_type supported")

    # Store pending auth info
    auth_state = generate_token()
    pending_auth[auth_state] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires": time.time() + 600  # 10 minutes
    }

    # Redirect to GitHub OAuth
    github_redirect = f"{BASE_URL}/oauth/github-callback"
    auth_url = (
        f"{GITHUB_AUTH_URL}?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={github_redirect}&"
        f"scope=read:user&"
        f"state={auth_state}"
    )

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/oauth/github-callback")
async def github_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = ""
):
    """
    GitHub OAuth callback.

    Handles both:
    1. Browser login (from /auth/login) - creates session cookie
    2. MCP OAuth (from /oauth/authorize) - returns authorization code
    """
    if error:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

    # Check if this is a browser login (oauth_state cookie from auth.py)
    browser_login_state = request.cookies.get("oauth_state")
    is_browser_login = browser_login_state and browser_login_state == state

    # For MCP OAuth, check pending_auth
    pending = None
    if not is_browser_login:
        pending = pending_auth.pop(state, None)
        if not pending:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        if pending["expires"] < time.time():
            raise HTTPException(status_code=400, detail="Authorization request expired")

    # Exchange GitHub code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{BASE_URL}/oauth/github-callback"
            },
            headers={"Accept": "application/json"}
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")

        token_data = token_response.json()
        github_token = token_data.get("access_token")

        if not github_token:
            raise HTTPException(status_code=400, detail="No access token from GitHub")

        # Get user info
        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/json"
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()
        username = user_data.get("login")

    # Handle browser login
    if is_browser_login:
        from api.auth import create_session, load_authorized_users, SESSION_COOKIE, SESSION_MAX_AGE

        # Check if user is authorized
        authorized_users = load_authorized_users()
        if authorized_users and username not in authorized_users:
            raise HTTPException(
                status_code=403,
                detail=f"User '{username}' is not authorized. Contact administrator."
            )

        # Create session
        session_token = create_session(username, github_token)

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

    # Handle MCP OAuth - generate authorization code
    auth_code = generate_token()
    auth_codes[auth_code] = {
        "client_id": pending["client_id"],
        "username": username,
        "github_token": github_token,
        "code_challenge": pending["code_challenge"],
        "code_challenge_method": pending["code_challenge_method"],
        "scope": pending["scope"],
        "expires": time.time() + 300  # 5 minutes
    }

    # Redirect back to client
    redirect_uri = pending["redirect_uri"]
    client_state = pending["state"]

    separator = "&" if "?" in redirect_uri else "?"
    redirect_url = f"{redirect_uri}{separator}code={auth_code}"
    if client_state:
        redirect_url += f"&state={client_state}"

    return RedirectResponse(url=redirect_url, status_code=302)


# Token Endpoint
@router.post("/oauth/token")
async def token_endpoint(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(default=""),
    redirect_uri: str = Form(default=""),
    client_id: str = Form(default=""),
    client_secret: str = Form(default=""),
    code_verifier: str = Form(default=""),
    refresh_token: str = Form(default="")
):
    """
    OAuth 2.0 Token Endpoint.

    Exchanges authorization code or refresh token for access token.
    """
    if grant_type == "authorization_code":
        # Validate code
        auth_data = auth_codes.pop(code, None)
        if not auth_data:
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        if auth_data["expires"] < time.time():
            raise HTTPException(status_code=400, detail="Authorization code expired")

        # Verify PKCE if code_challenge was provided
        if auth_data["code_challenge"]:
            if not code_verifier:
                raise HTTPException(status_code=400, detail="code_verifier required")

            if not verify_pkce(code_verifier, auth_data["code_challenge"], auth_data["code_challenge_method"]):
                raise HTTPException(status_code=400, detail="Invalid code_verifier")

        # Generate tokens
        access_token = generate_token()
        new_refresh_token = generate_token()

        access_tokens[access_token] = {
            "client_id": auth_data["client_id"],
            "username": auth_data["username"],
            "scope": auth_data["scope"],
            "expires": time.time() + ACCESS_TOKEN_EXPIRY
        }

        refresh_tokens[new_refresh_token] = {
            "client_id": auth_data["client_id"],
            "username": auth_data["username"],
            "scope": auth_data["scope"],
            "expires": time.time() + REFRESH_TOKEN_EXPIRY
        }

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRY,
            "refresh_token": new_refresh_token,
            "scope": auth_data["scope"]
        }

    elif grant_type == "refresh_token":
        # Validate refresh token
        token_data = refresh_tokens.get(refresh_token)
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        if token_data["expires"] < time.time():
            del refresh_tokens[refresh_token]
            raise HTTPException(status_code=400, detail="Refresh token expired")

        # Generate new access token
        access_token = generate_token()

        access_tokens[access_token] = {
            "client_id": token_data["client_id"],
            "username": token_data["username"],
            "scope": token_data["scope"],
            "expires": time.time() + ACCESS_TOKEN_EXPIRY
        }

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRY,
            "scope": token_data["scope"]
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


# Token Revocation
@router.post("/oauth/revoke")
async def revoke_token(
    request: Request,
    token: str = Form(...),
    token_type_hint: str = Form(default="access_token")
):
    """
    OAuth 2.0 Token Revocation.

    Revokes an access token or refresh token.
    """
    # Try to revoke as access token
    if token in access_tokens:
        del access_tokens[token]
        return {"revoked": True}

    # Try to revoke as refresh token
    if token in refresh_tokens:
        del refresh_tokens[token]
        return {"revoked": True}

    # Token not found is still a success per RFC 7009
    return {"revoked": True}


# Token validation helper (for use by other modules)
def validate_bearer_token(token: str) -> Optional[dict]:
    """
    Validate a Bearer token.

    Args:
        token: The Bearer token to validate

    Returns:
        dict: Token data if valid, None otherwise
    """
    token_data = access_tokens.get(token)
    if not token_data:
        return None

    if token_data["expires"] < time.time():
        del access_tokens[token]
        return None

    return token_data
