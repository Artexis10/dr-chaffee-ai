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
from ..services.discord_roles_loader import (
    resolve_user_tier,
    get_tier_label,
    get_tier_color,
    get_all_tiers,
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
    discord_tier: Optional[str] = None,
) -> int:
    """
    Create or update a user record based on Discord ID.
    
    Args:
        discord_id: Discord user ID
        username: Discord username
        discriminator: Discord discriminator (legacy, may be None)
        global_name: Discord display name
        avatar: Discord avatar hash
        discord_tier: Resolved membership tier from Discord roles
    
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
                discord_tier,
                last_login_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (discord_id) DO UPDATE SET
                discord_username = EXCLUDED.discord_username,
                discord_discriminator = EXCLUDED.discord_discriminator,
                discord_global_name = EXCLUDED.discord_global_name,
                discord_avatar = EXCLUDED.discord_avatar,
                discord_tier = EXCLUDED.discord_tier,
                last_login_at = NOW(),
                updated_at = NOW()
            RETURNING id
        """, (discord_id, username, discriminator, global_name, avatar, discord_tier))
        
        result = cur.fetchone()
        conn.commit()
        
        return result['id']
        
    finally:
        conn.close()


def get_user_by_discord_id(discord_id: str) -> Optional[dict]:
    """
    Fetch a user record by Discord ID.
    
    Returns:
        User dict with id, discord_id, discord_username, discord_global_name,
        discord_avatar, discord_tier, or None if not found.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                id,
                discord_id,
                discord_username,
                discord_global_name,
                discord_avatar,
                discord_tier,
                created_at,
                last_login_at
            FROM users
            WHERE discord_id = %s
        """, (discord_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
        
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
    
    logger.info(f"Initiating Discord OAuth flow (redirect_uri: {config.redirect_uri})")
    
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
    member_roles = member.get('roles', [])
    if not user_has_allowed_role(member, config.allowed_role_ids):
        logger.info(f"User {discord_id} lacks required roles. Has: {member_roles}, needs one of: {config.allowed_role_ids}")
        # Clear state cookie and redirect to insufficient-role page
        redirect = RedirectResponse(
            url=f"{frontend_url}/auth/discord/insufficient-role",
            status_code=302
        )
        redirect.delete_cookie(STATE_COOKIE_NAME, path="/")
        return redirect
    
    # Resolve user's tier from their Discord roles
    user_tier = resolve_user_tier(member_roles)
    if user_tier:
        logger.info(f"User {discord_id} resolved to tier: {user_tier}")
    else:
        logger.info(f"User {discord_id} has no matching tier (roles: {member_roles})")
    
    # All checks passed - upsert user in database
    try:
        user_id = upsert_discord_user(
            discord_id=discord_id,
            username=username,
            discriminator=discriminator,
            global_name=global_name,
            avatar=avatar,
            discord_tier=user_tier,
        )
        logger.info(f"User upserted: id={user_id}, discord_id={discord_id}, tier={user_tier}")
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
    
    # Set discord_user_id cookie for /me endpoint to fetch user data
    redirect.set_cookie(
        key="discord_user_id",
        value=discord_id,
        max_age=max_age,
        httponly=True,  # Not needed by frontend JS
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
    The 'enabled' field is the primary indicator for frontend to show/hide Discord login.
    """
    config = get_discord_config()
    is_configured = config.is_configured()
    
    return {
        "enabled": is_configured,  # Primary field for frontend
        "configured": is_configured,  # Legacy field for backwards compatibility
        "missing": config.get_missing_config() if not is_configured else [],
        "guild_id": config.guild_id if is_configured else None,
        "role_count": len(config.allowed_role_ids) if is_configured else 0,
    }


@router.get("/me")
async def get_current_user(request: Request):
    """
    Get current authenticated user's information.
    
    Requires valid auth_token cookie (set by Discord OAuth callback).
    
    Returns:
        User info including discord_tier and discord_tier_label.
    """
    # Get auth token from cookie
    auth_token = request.cookies.get("auth_token")
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify token signature and expiry
    import hmac
    import hashlib
    import base64
    import json
    import time
    
    secret = os.getenv("APP_SESSION_SECRET", "")
    if not secret:
        if os.getenv("NODE_ENV") != "production":
            secret = "dev-only-secret-do-not-use-in-production"
        else:
            raise HTTPException(status_code=500, detail="APP_SESSION_SECRET not configured")
    
    try:
        parts = auth_token.split(".")
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        payload_b64, signature_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip('=')
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            raise HTTPException(status_code=401, detail="Invalid token signature")
        
        # Decode and check expiry
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token expired")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Token is valid, but we need to get user info
    # Since the token doesn't contain user ID, we need to get it from a cookie or session
    # For now, we'll use a discord_user_id cookie that's set alongside auth_token
    discord_id = request.cookies.get("discord_user_id")
    if not discord_id:
        # Fallback: return minimal info indicating authenticated but no user data
        return {
            "authenticated": True,
            "discord_id": None,
            "discord_username": None,
            "discord_global_name": None,
            "discord_avatar": None,
            "discord_tier": None,
            "discord_tier_label": None,
            "discord_tier_color": None,
        }
    
    # Fetch user from database
    user = get_user_by_discord_id(discord_id)
    if not user:
        return {
            "authenticated": True,
            "discord_id": discord_id,
            "discord_username": None,
            "discord_global_name": None,
            "discord_avatar": None,
            "discord_tier": None,
            "discord_tier_label": None,
            "discord_tier_color": None,
        }
    
    tier = user.get("discord_tier")
    tier_label = get_tier_label(tier) if tier else None
    tier_color = get_tier_color(tier) if tier else None
    
    return {
        "authenticated": True,
        "id": user.get("id"),
        "discord_id": user.get("discord_id"),
        "discord_username": user.get("discord_username"),
        "discord_global_name": user.get("discord_global_name"),
        "discord_avatar": user.get("discord_avatar"),
        "discord_tier": tier,
        "discord_tier_label": tier_label,
        "discord_tier_color": tier_color,
    }


@router.get("/tiers")
async def get_available_tiers():
    """
    Get list of available membership tiers.
    
    Returns:
        List of tiers with id, name, and color, ordered by priority (highest first).
        
    Example response:
        {
            "tiers": [
                {"id": "paragon_of_virtue", "name": "Paragon of Virtue", "color": "#C27C0E"},
                {"id": "exclusive", "name": "Exclusive", "color": "#F1C40F"},
                {"id": "vip", "name": "VIP", "color": "#95A5A6"},
                {"id": "all_access", "name": "All Access", "color": "#3498DB"}
            ]
        }
    """
    tiers = get_all_tiers()
    return {"tiers": tiers}
