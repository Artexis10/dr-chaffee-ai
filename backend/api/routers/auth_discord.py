"""
Discord OAuth Authentication Router

Provides endpoints for Discord OAuth2 authentication flow:
- GET /auth/discord/login - Initiates OAuth flow
- GET /auth/discord/callback - Handles OAuth callback

After successful authentication:
1. Validates user is in required guild
2. Validates user has at least one allowed role
3. Upserts user record in database
4. Issues auth_token cookie (same as password login)
5. Redirects to frontend app
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import psycopg2
from psycopg2.extras import RealDictCursor

from ..services.discord_client import (
    get_discord_config,
    generate_state_token,
    build_discord_authorize_url,
    exchange_code_for_token,
    get_discord_user,
    get_guild_member,
    user_has_allowed_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/discord", tags=["discord-auth"])

# Cookie settings
STATE_COOKIE_NAME = "discord_oauth_state"
STATE_COOKIE_MAX_AGE = 600  # 10 minutes


def get_db_connection():
    """Get database connection."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Parse connection string
    # Handle both postgres:// and postgresql:// schemes
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def create_session_token() -> str:
    """
    Create a signed session token compatible with the frontend auth system.
    
    This replicates the token format from frontend/src/utils/authToken.ts
    to ensure middleware compatibility.
    """
    import hmac
    import hashlib
    import base64
    import json
    import time
    
    # Get session secret (same as frontend uses)
    secret = os.getenv("APP_SESSION_SECRET", "")
    if not secret:
        # In dev, use fallback (matches frontend behavior)
        if os.getenv("NODE_ENV") != "production":
            secret = "dev-only-secret-do-not-use-in-production"
        else:
            raise HTTPException(status_code=500, detail="APP_SESSION_SECRET not configured")
    
    # Token expiry: 7 days
    now = int(time.time())
    expiry = now + (7 * 24 * 60 * 60)
    
    payload = {"iat": now, "exp": expiry}
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Base64url encode payload
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
    
    # Create HMAC-SHA256 signature
    signature = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    return f"{payload_b64}.{signature_b64}"


def upsert_discord_user(
    discord_id: str,
    username: str,
    discriminator: Optional[str],
    global_name: Optional[str],
    avatar: Optional[str],
) -> int:
    """
    Create or update a user record based on Discord ID.
    
    Returns:
        User ID from database
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Upsert user - update if exists, insert if not
        cur.execute("""
            INSERT INTO users (
                discord_id, 
                discord_username, 
                discord_discriminator, 
                discord_global_name,
                discord_avatar,
                last_login_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (discord_id) DO UPDATE SET
                discord_username = EXCLUDED.discord_username,
                discord_discriminator = EXCLUDED.discord_discriminator,
                discord_global_name = EXCLUDED.discord_global_name,
                discord_avatar = EXCLUDED.discord_avatar,
                last_login_at = NOW(),
                updated_at = NOW()
            RETURNING id
        """, (discord_id, username, discriminator, global_name, avatar))
        
        result = cur.fetchone()
        conn.commit()
        
        return result['id']
        
    finally:
        conn.close()


@router.get("/login")
async def discord_login(request: Request, response: Response):
    """
    Initiate Discord OAuth flow.
    
    1. Generate secure state token
    2. Store state in HttpOnly cookie
    3. Redirect to Discord authorization URL
    """
    config = get_discord_config()
    
    if not config.is_configured():
        missing = config.get_missing_config()
        logger.error(f"Discord OAuth not configured. Missing: {missing}")
        raise HTTPException(
            status_code=503,
            detail=f"Discord OAuth not configured. Missing: {', '.join(missing)}"
        )
    
    # Generate state token for CSRF protection
    state = generate_state_token()
    
    # Build authorization URL
    auth_url = build_discord_authorize_url(state)
    
    logger.info(f"Initiating Discord OAuth flow, redirecting to Discord")
    
    # Create redirect response
    redirect = RedirectResponse(url=auth_url, status_code=302)
    
    # Set state cookie (HttpOnly, Secure in production)
    is_production = os.getenv("NODE_ENV") == "production"
    redirect.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        max_age=STATE_COOKIE_MAX_AGE,
        httponly=True,
        secure=is_production,
        samesite="lax",
        path="/",
    )
    
    return redirect


@router.get("/callback")
async def discord_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Handle Discord OAuth callback.
    
    1. Validate state against cookie
    2. Exchange code for access token
    3. Fetch user info and guild membership
    4. Check role requirements
    5. Upsert user in database
    6. Issue auth_token cookie
    7. Redirect to frontend
    """
    config = get_discord_config()
    frontend_url = config.frontend_url
    
    # Handle OAuth errors from Discord
    if error:
        logger.error(f"Discord OAuth error: {error} - {error_description}")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error={error}",
            status_code=302
        )
    
    # Validate required parameters
    if not code or not state:
        logger.error("Missing code or state in callback")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=missing_params",
            status_code=302
        )
    
    # Validate state against cookie
    stored_state = request.cookies.get(STATE_COOKIE_NAME)
    if not stored_state or stored_state != state:
        logger.error("State mismatch - possible CSRF attack")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=invalid_state",
            status_code=302
        )
    
    # Exchange code for token
    token_response = await exchange_code_for_token(code)
    if not token_response:
        logger.error("Failed to exchange code for token")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=token_exchange_failed",
            status_code=302
        )
    
    access_token = token_response.get("access_token")
    if not access_token:
        logger.error("No access token in response")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=no_access_token",
            status_code=302
        )
    
    # Fetch user info
    user = await get_discord_user(access_token)
    if not user:
        logger.error("Failed to fetch Discord user")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=user_fetch_failed",
            status_code=302
        )
    
    discord_id = user.get("id")
    username = user.get("username", "")
    discriminator = user.get("discriminator")
    global_name = user.get("global_name")
    avatar = user.get("avatar")
    
    logger.info(f"Discord user authenticated: {username} ({discord_id})")
    
    # Check guild membership
    member = await get_guild_member(access_token, config.guild_id)
    if not member:
        logger.info(f"User {discord_id} is not in guild {config.guild_id}")
        # Clear state cookie and redirect to not-in-server page
        redirect = RedirectResponse(
            url=f"{frontend_url}/auth/discord/not-in-server",
            status_code=302
        )
        redirect.delete_cookie(STATE_COOKIE_NAME, path="/")
        return redirect
    
    # Check role requirements
    if not user_has_allowed_role(member, config.allowed_role_ids):
        logger.info(f"User {discord_id} lacks required roles. Has: {member.get('roles', [])}, needs one of: {config.allowed_role_ids}")
        # Clear state cookie and redirect to insufficient-role page
        redirect = RedirectResponse(
            url=f"{frontend_url}/auth/discord/insufficient-role",
            status_code=302
        )
        redirect.delete_cookie(STATE_COOKIE_NAME, path="/")
        return redirect
    
    # All checks passed - upsert user in database
    try:
        user_id = upsert_discord_user(
            discord_id=discord_id,
            username=username,
            discriminator=discriminator,
            global_name=global_name,
            avatar=avatar,
        )
        logger.info(f"User upserted: id={user_id}, discord_id={discord_id}")
    except Exception as e:
        logger.error(f"Failed to upsert user: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=database_error",
            status_code=302
        )
    
    # Create session token (same format as password login)
    try:
        auth_token = create_session_token()
    except Exception as e:
        logger.error(f"Failed to create session token: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=token_creation_failed",
            status_code=302
        )
    
    # Success! Redirect to frontend with auth cookie
    redirect = RedirectResponse(url=frontend_url, status_code=302)
    
    # Set auth_token cookie (same as password login does)
    is_production = os.getenv("NODE_ENV") == "production"
    max_age = 7 * 24 * 60 * 60  # 7 days
    
    redirect.set_cookie(
        key="auth_token",
        value=auth_token,
        max_age=max_age,
        httponly=False,  # Match existing behavior - frontend reads from localStorage
        secure=is_production,
        samesite="lax",
        path="/",
    )
    
    # Delete state cookie
    redirect.delete_cookie(STATE_COOKIE_NAME, path="/")
    
    logger.info(f"Discord login successful for user {discord_id}, redirecting to {frontend_url}")
    
    return redirect


@router.get("/status")
async def discord_auth_status():
    """
    Check if Discord OAuth is configured.
    
    Returns configuration status (not secrets).
    """
    config = get_discord_config()
    
    return {
        "configured": config.is_configured(),
        "missing": config.get_missing_config() if not config.is_configured() else [],
        "guild_id": config.guild_id if config.is_configured() else None,
        "role_count": len(config.allowed_role_ids) if config.is_configured() else 0,
    }
