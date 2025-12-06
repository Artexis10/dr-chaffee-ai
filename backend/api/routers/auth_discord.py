"""
Discord OAuth Authentication Router

Provides endpoints for Discord OAuth2 authentication flow:
- GET /api/auth/discord/login - Initiates OAuth flow
- GET /api/auth/discord/callback - Handles OAuth callback

After successful authentication:
1. Validates user is in required guild
2. Validates user has at least one allowed role
3. Upserts user record in database
4. Issues auth_token cookie (same as password login)
5. Redirects to frontend app

STATE MANAGEMENT:
We use a SERVER-SIDE state store (not cookies) to avoid cross-domain/SameSite issues.
The state is stored in an in-memory TTL cache with 10-minute expiry.
This is more robust than cookie-based state because:
- No cookie domain/path issues between frontend and backend hosts
- No SameSite restrictions on cross-site redirects from Discord
- State is validated server-side, not dependent on browser cookie handling
"""

import os
import logging
import time
import threading
from datetime import datetime
from typing import Optional, Dict

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
from ..services.auth_tokens import (
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    decode_and_validate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/discord", tags=["discord-auth"])

# ============================================
# SERVER-SIDE STATE STORE
# ============================================
# Using in-memory store instead of cookies to avoid cross-domain issues.
# State tokens expire after 10 minutes and are single-use.

STATE_TTL_SECONDS = 600  # 10 minutes
_state_store: Dict[str, float] = {}  # state -> expiry_timestamp
_state_lock = threading.Lock()


def _cleanup_expired_states():
    """Remove expired states from the store."""
    now = time.time()
    with _state_lock:
        expired = [s for s, exp in _state_store.items() if exp < now]
        for s in expired:
            del _state_store[s]


def store_oauth_state(state: str) -> None:
    """
    Store an OAuth state token with TTL.
    
    Args:
        state: The state token to store
    """
    _cleanup_expired_states()
    expiry = time.time() + STATE_TTL_SECONDS
    with _state_lock:
        _state_store[state] = expiry
    logger.info(f"Stored OAuth state (server-side): ...{state[-8:]}, expires in {STATE_TTL_SECONDS}s")


def validate_and_consume_state(state: str) -> bool:
    """
    Validate and consume an OAuth state token.
    
    Returns True if state is valid and not expired, False otherwise.
    State is removed after validation (single-use).
    
    Args:
        state: The state token to validate
        
    Returns:
        True if valid, False otherwise
    """
    _cleanup_expired_states()
    now = time.time()
    
    with _state_lock:
        if state not in _state_store:
            logger.warning(f"OAuth state not found in store: ...{state[-8:] if state else 'None'}")
            return False
        
        expiry = _state_store[state]
        if expiry < now:
            logger.warning(f"OAuth state expired: ...{state[-8:]}")
            del _state_store[state]
            return False
        
        # Valid - consume it (single-use)
        del _state_store[state]
        logger.info(f"OAuth state validated and consumed: ...{state[-8:]}")
        return True


# Legacy cookie name (kept for backwards compatibility during transition)
STATE_COOKIE_NAME = "discord_oauth_state"


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


# Legacy create_session_token removed - now using auth_tokens service
# See backend/api/services/auth_tokens.py for JWT token creation


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
    2. Store state in SERVER-SIDE cache (not cookie - avoids cross-domain issues)
    3. Redirect to Discord authorization URL
    
    NOTE: We use server-side state storage instead of cookies because:
    - Cookie-based state was causing invalid_state errors due to SameSite/cross-domain issues
    - Server-side state is more reliable across different browser configurations
    - State is single-use and expires after 10 minutes
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
    
    # Store state in server-side cache (NOT cookie)
    store_oauth_state(state)
    
    # Build authorization URL
    auth_url = build_discord_authorize_url(state)
    
    logger.info(f"Initiating Discord OAuth flow (redirect_uri: {config.redirect_uri}, state: ...{state[-8:]})")
    
    # Create redirect response - no state cookie needed
    redirect = RedirectResponse(url=auth_url, status_code=302)
    
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
    
    1. Validate state against SERVER-SIDE store (not cookie)
    2. Exchange code for access token
    3. Fetch user info and guild membership
    4. Check role requirements
    5. Upsert user in database
    6. Issue auth_token cookie
    7. Redirect to frontend
    
    NOTE: State validation uses server-side store, not cookies.
    This avoids cross-domain/SameSite issues that were causing invalid_state errors.
    """
    config = get_discord_config()
    frontend_url = config.frontend_url
    
    logger.info(f"Discord OAuth callback received (state: ...{state[-8:] if state else 'None'})")
    
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
    
    # Validate state against SERVER-SIDE store (not cookie)
    # This is more robust than cookie-based validation
    if not validate_and_consume_state(state):
        logger.error(f"State validation failed - state not found or expired: ...{state[-8:]}")
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
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/not-in-server",
            status_code=302
        )
    
    # Check role requirements
    member_roles = member.get('roles', [])
    if not user_has_allowed_role(member, config.allowed_role_ids):
        logger.info(f"User {discord_id} lacks required roles. Has: {member_roles}, needs one of: {config.allowed_role_ids}")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/insufficient-role",
            status_code=302
        )
    
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
    
    # Create JWT tokens (same as password login - unified auth)
    try:
        extra_claims = {
            "discord_id": discord_id,
            "tier": user_tier,
            "username": username,
        }
        access_token = create_access_token(user_id, extra_claims)
        refresh_token = create_refresh_token(user_id, {"discord_id": discord_id})
    except Exception as e:
        logger.error(f"Failed to create tokens: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/auth/discord/error?error=token_creation_failed",
            status_code=302
        )
    
    # Success! Redirect to frontend with auth cookies
    # NOTE: Discord OAuth is for the MAIN APP only, NOT the tuning dashboard.
    # Tuning dashboard uses password-only authentication via /api/tuning/auth/verify.
    redirect = RedirectResponse(url=frontend_url, status_code=302)
    
    # Set JWT tokens as HttpOnly cookies (tokens never exposed to JS)
    set_auth_cookies(redirect, access_token, refresh_token)
    
    # NOTE: We do NOT set tuning_auth cookie here.
    # Tuning dashboard access requires separate password authentication.
    # This keeps the admin panel isolated from Discord OAuth.
    
    # NOTE: No state cookie to delete - we use server-side state store now
    
    logger.info(f"Discord login successful for user_id={user_id}, discord_id={discord_id}")
    
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
    
    # Include redirect_uri for debugging (not a secret - it's visible in the OAuth URL)
    # This helps verify the redirect_uri matches what's in Discord Developer Portal
    return {
        "enabled": is_configured,  # Primary field for frontend
        "configured": is_configured,  # Legacy field for backwards compatibility
        "missing": config.get_missing_config() if not is_configured else [],
        "guild_id": config.guild_id if is_configured else None,
        "role_count": len(config.allowed_role_ids) if is_configured else 0,
        "redirect_uri": config.redirect_uri if is_configured else None,  # For debugging OAuth mismatches
    }


@router.get("/me")
async def get_current_discord_user(request: Request):
    """
    Get current Discord user's information.
    
    DEPRECATED: Use /api/auth/me instead for unified auth.
    This endpoint is kept for backwards compatibility.
    
    Requires valid access_token cookie (JWT).
    
    Returns:
        User info including discord_tier and discord_tier_label.
    """
    # Try new JWT access token first
    access_token = request.cookies.get("access_token")
    
    user_id = None
    discord_id = None
    
    if access_token:
        payload = decode_and_validate(access_token, "access")
        if payload:
            user_id = int(payload["sub"])
            discord_id = payload.get("discord_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # If we have discord_id from token, use it; otherwise fetch from DB
    if not discord_id:
        # Fetch user to get discord_id
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT discord_id FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            if result:
                discord_id = result["discord_id"]
        finally:
            conn.close()
    
    if not discord_id or discord_id == "password_user_local":
        # Not a Discord user
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
    
    # Fetch full user from database
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
