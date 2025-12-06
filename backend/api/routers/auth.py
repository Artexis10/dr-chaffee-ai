"""
Unified Authentication Router

Provides endpoints for:
- GET /api/auth/me - Get current user with automatic token refresh
- POST /api/auth/logout - Clear auth cookies
- POST /api/auth/login - Password-based login (issues same tokens as Discord)

Security:
- All tokens are HttpOnly cookies only
- Tokens never appear in responses, logs, or URLs
- CSRF protection via SameSite cookies + JSON-only endpoints
- Explicit HS256 algorithm enforcement
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services.auth_tokens import (
    create_access_token,
    create_refresh_token,
    decode_and_validate,
    set_auth_cookies,
    clear_auth_cookies,
    ACCESS_TOKEN_LIFETIME_SECONDS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================
# Database helpers (reuse from auth_discord)
# ============================================

def _get_db_connection():
    """Get database connection."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def _get_user_by_id(user_id: int) -> Optional[dict]:
    """Fetch user by internal ID."""
    conn = _get_db_connection()
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
            WHERE id = %s
        """, (user_id,))
        result = cur.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()


def _get_or_create_password_user() -> int:
    """
    Get or create a user record for password-based authentication.
    
    Password users don't have Discord info, so we use a special marker.
    Returns the user ID.
    """
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        
        # Use a special discord_id marker for password users
        password_user_marker = "password_user_local"
        
        cur.execute("""
            INSERT INTO users (
                discord_id,
                discord_username,
                last_login_at,
                updated_at
            )
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (discord_id) DO UPDATE SET
                last_login_at = NOW(),
                updated_at = NOW()
            RETURNING id
        """, (password_user_marker, "Password User"))
        
        result = cur.fetchone()
        conn.commit()
        return result['id']
    finally:
        conn.close()


# ============================================
# Tier helpers (import from discord roles)
# ============================================

def _get_tier_info(tier: Optional[str]) -> tuple:
    """Get tier label and color."""
    try:
        from ..services.discord_roles_loader import get_tier_label, get_tier_color
        label = get_tier_label(tier) if tier else None
        color = get_tier_color(tier) if tier else None
        return label, color
    except Exception:
        return None, None


# ============================================
# Request models
# ============================================

class PasswordLoginRequest(BaseModel):
    password: str


# ============================================
# Endpoints
# ============================================

@router.get("/me")
async def get_current_user(
    request: Request,
    response: Response,
    x_requested_with: Optional[str] = Header(None),
):
    """
    Get current authenticated user.
    
    Behavior:
    1. If access_token valid → return user info
    2. If access_token expired but refresh_token valid → mint new tokens, return user
    3. If both invalid → return 401
    
    Response includes:
    - authenticated: bool
    - user: { id, displayName, discordId, discordAvatar, tier, tierLabel, tierColor }
    
    Security:
    - Tokens are never included in response
    - Only sanitized user data is returned
    """
    # Try access token first
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    user_id = None
    needs_token_refresh = False
    
    # Validate access token
    if access_token:
        payload = decode_and_validate(access_token, "access")
        if payload:
            user_id = int(payload["sub"])
            logger.debug(f"[Auth /me] Valid access token for user_id={user_id}")
    
    # If no valid access token, try refresh token
    if not user_id and refresh_token:
        payload = decode_and_validate(refresh_token, "refresh")
        if payload:
            user_id = int(payload["sub"])
            needs_token_refresh = True
            logger.debug(f"[Auth /me] Using refresh token for user_id={user_id}")
    
    # NOTE: Legacy auth_token cookies are no longer checked.
    # Users with only legacy tokens must re-login to get new JWT tokens.
    
    if not user_id:
        logger.debug("[Auth /me] No valid tokens found")
        return JSONResponse(
            status_code=401,
            content={"detail": "not_authenticated", "authenticated": False}
        )
    
    # Fetch user from database
    user = _get_user_by_id(user_id)
    if not user:
        logger.warning(f"[Auth /me] User not found in database: user_id={user_id}")
        # Clear invalid cookies
        clear_auth_cookies(response)
        return JSONResponse(
            status_code=401,
            content={"detail": "user_not_found", "authenticated": False}
        )
    
    # Refresh tokens if needed
    if needs_token_refresh:
        extra = {}
        if user.get("discord_id") and user["discord_id"] != "password_user_local":
            extra["discord_id"] = user["discord_id"]
        if user.get("discord_tier"):
            extra["tier"] = user["discord_tier"]
        
        new_access = create_access_token(user_id, extra)
        new_refresh = create_refresh_token(user_id, extra)
        set_auth_cookies(response, new_access, new_refresh)
        logger.info(f"[Auth /me] Refreshed tokens for user_id={user_id}")
    
    # Build sanitized response
    tier = user.get("discord_tier")
    tier_label, tier_color = _get_tier_info(tier)
    
    # Determine display name
    display_name = (
        user.get("discord_global_name") or 
        user.get("discord_username") or 
        "User"
    )
    
    # Check if this is a Discord user or password user
    is_discord_user = (
        user.get("discord_id") and 
        user["discord_id"] != "password_user_local"
    )
    
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "displayName": display_name,
            "discordId": user.get("discord_id") if is_discord_user else None,
            "discordUsername": user.get("discord_username") if is_discord_user else None,
            "discordAvatar": user.get("discord_avatar") if is_discord_user else None,
            "tier": tier,
            "tierLabel": tier_label,
            "tierColor": tier_color,
            "isDiscordUser": is_discord_user,
        }
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    x_requested_with: Optional[str] = Header(None),
):
    """
    Log out the current user by clearing all auth cookies.
    
    Security:
    - Clears both access and refresh tokens
    - Also clears legacy auth_token for clean transition
    - Returns success even if not logged in (idempotent)
    """
    clear_auth_cookies(response)
    
    logger.info("[Auth] User logged out")
    
    return {"success": True, "message": "Logged out"}


@router.post("/login")
async def password_login(
    request: Request,
    response: Response,
    body: PasswordLoginRequest,
    x_requested_with: Optional[str] = Header(None),
):
    """
    Password-based login endpoint.
    
    Validates password against APP_PASSWORD env var and issues
    the same JWT tokens as Discord OAuth login.
    
    Security:
    - Tokens are set as HttpOnly cookies only
    - Tokens are NEVER returned in the response body
    - Password is validated server-side only
    """
    app_password = os.getenv("APP_PASSWORD", "")
    
    if not app_password:
        logger.warning("[Auth] Password login attempted but APP_PASSWORD not configured")
        raise HTTPException(status_code=403, detail="Password login not configured")
    
    if body.password != app_password:
        logger.warning("[Auth] Invalid password attempt")
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Get or create password user
    try:
        user_id = _get_or_create_password_user()
    except Exception as e:
        logger.error(f"[Auth] Failed to get/create password user: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")
    
    # Create tokens (same as Discord OAuth)
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    # Set cookies (tokens never in response body)
    set_auth_cookies(response, access_token, refresh_token)
    
    logger.info(f"[Auth] Password login successful for user_id={user_id}")
    
    # Return success without tokens
    return {
        "success": True,
        "message": "Login successful"
        # NOTE: Tokens are in cookies, not in this response
    }
