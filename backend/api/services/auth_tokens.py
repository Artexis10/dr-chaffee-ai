"""
JWT Token Service for Unified Authentication

Provides secure JWT access and refresh token management for both
Discord OAuth and password-based authentication.

Security features:
- HS256 algorithm explicitly enforced
- HttpOnly + Secure cookies only
- Tokens never exposed in responses, logs, or URLs
- Short-lived access tokens (8h) + long-lived refresh tokens (30d)
- Type claim to distinguish access vs refresh tokens

Environment variables:
- AUTH_SESSION_SECRET: Required secret for signing JWTs (min 32 chars recommended)
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

# Token lifetimes
ACCESS_TOKEN_LIFETIME_SECONDS = 8 * 60 * 60  # 8 hours
REFRESH_TOKEN_LIFETIME_SECONDS = 30 * 24 * 60 * 60  # 30 days

# Cookie settings
COOKIE_PATH = "/"
COOKIE_SAMESITE_ACCESS = "lax"
COOKIE_SAMESITE_REFRESH = "lax"  # Using lax for both to ensure cross-page navigation works

# JWT algorithm - explicitly enforced
JWT_ALGORITHM = "HS256"


def _get_secret() -> str:
    """
    Get the JWT signing secret from environment.
    
    Raises ValueError in production if not configured.
    Uses a dev-only fallback in development (with warning).
    """
    secret = os.getenv("AUTH_SESSION_SECRET", "")
    
    if not secret:
        # Also check legacy env var for backwards compatibility
        secret = os.getenv("APP_SESSION_SECRET", "")
    
    if not secret:
        # Use the same production detection as _is_production()
        # (defined below, but we inline the check here to avoid circular dependency)
        is_prod = (
            os.getenv("NODE_ENV") == "production" or
            os.getenv("PYTHON_ENV") == "production" or
            os.getenv("RENDER") == "true" or
            os.getenv("RAILWAY_ENVIRONMENT") == "production" or
            os.getenv("VERCEL_ENV") == "production" or
            bool(os.getenv("HEROKU_APP_NAME")) or
            bool(os.getenv("FLY_APP_NAME")) or
            os.getenv("FRONTEND_URL", "").startswith("https://")
        )
        if is_prod:
            raise ValueError("AUTH_SESSION_SECRET must be set in production")
        # Dev fallback
        logger.warning("[Auth] Using dev-only secret. Set AUTH_SESSION_SECRET in production.")
        return "dev-only-jwt-secret-do-not-use-in-production-min32chars"
    
    return secret


def _is_production() -> bool:
    """
    Check if running in production mode.
    
    Checks multiple environment indicators to ensure Secure cookies
    are set correctly across different deployment platforms.
    """
    # Explicit production flag
    if os.getenv("NODE_ENV") == "production":
        return True
    if os.getenv("PYTHON_ENV") == "production":
        return True
    
    # Platform-specific indicators
    if os.getenv("RENDER") == "true":  # Render.com
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") == "production":  # Railway
        return True
    if os.getenv("VERCEL_ENV") == "production":  # Vercel
        return True
    if os.getenv("HEROKU_APP_NAME"):  # Heroku (any deployed app)
        return True
    if os.getenv("FLY_APP_NAME"):  # Fly.io
        return True
    
    # Check if HTTPS is being used (via proxy headers)
    # This is a fallback for platforms that don't set specific env vars
    frontend_url = os.getenv("FRONTEND_URL", "")
    if frontend_url.startswith("https://"):
        return True
    
    return False


def create_access_token(
    user_id: int,
    extra: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a short-lived access token (8 hours).
    
    Args:
        user_id: Internal database user ID
        extra: Optional additional claims (e.g., discord_id, tier)
    
    Returns:
        Signed JWT string
        
    Note: Token is NEVER logged or returned in API responses.
    """
    now = int(time.time())
    
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_LIFETIME_SECONDS,
    }
    
    if extra:
        # Only include safe, non-sensitive extra claims
        safe_keys = {"discord_id", "tier", "username"}
        for key in safe_keys:
            if key in extra:
                payload[key] = extra[key]
    
    token = jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)
    
    # Log only that a token was created, never the token itself
    logger.debug(f"[Auth] Created access token for user_id={user_id}")
    
    return token


def create_refresh_token(
    user_id: int,
    extra: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a long-lived refresh token (30 days).
    
    Args:
        user_id: Internal database user ID
        extra: Optional additional claims
    
    Returns:
        Signed JWT string
        
    Note: Token is NEVER logged or returned in API responses.
    """
    now = int(time.time())
    
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_LIFETIME_SECONDS,
    }
    
    if extra:
        safe_keys = {"discord_id"}
        for key in safe_keys:
            if key in extra:
                payload[key] = extra[key]
    
    token = jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)
    
    logger.debug(f"[Auth] Created refresh token for user_id={user_id}")
    
    return token


def decode_and_validate(
    token: str,
    expected_type: str
) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT string to validate
        expected_type: Expected token type ("access" or "refresh")
    
    Returns:
        Decoded payload dict if valid, None otherwise
        
    Security:
    - Explicitly enforces HS256 algorithm
    - Validates expiration
    - Validates token type claim
    """
    if not token:
        return None
    
    try:
        # Explicitly specify allowed algorithms to prevent algorithm confusion attacks
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]}
        )
        
        # Validate token type
        if payload.get("type") != expected_type:
            logger.warning(f"[Auth] Token type mismatch: expected={expected_type}, got={payload.get('type')}")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug("[Auth] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[Auth] Invalid token: {type(e).__name__}")
        return None
    except Exception as e:
        logger.error(f"[Auth] Token validation error: {type(e).__name__}")
        return None


def set_auth_cookies(
    response,
    access_token: str,
    refresh_token: str
) -> None:
    """
    Set access and refresh token cookies on a response.
    
    Args:
        response: FastAPI Response or RedirectResponse
        access_token: The access token JWT
        refresh_token: The refresh token JWT
        
    Cookie settings:
    - HttpOnly: True (never accessible to JavaScript)
    - Secure: True in production (HTTPS only)
    - SameSite: Lax (CSRF protection while allowing navigation)
    - Path: / (available to all routes)
    """
    is_prod = _is_production()
    
    # Access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
        httponly=True,
        secure=is_prod,
        samesite=COOKIE_SAMESITE_ACCESS,
        path=COOKIE_PATH,
    )
    
    # Refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_LIFETIME_SECONDS,
        httponly=True,
        secure=is_prod,
        samesite=COOKIE_SAMESITE_REFRESH,
        path=COOKIE_PATH,
    )
    
    logger.debug("[Auth] Set auth cookies on response")


def clear_auth_cookies(response) -> None:
    """
    Clear all auth cookies by setting them to empty with max_age=0.
    
    Args:
        response: FastAPI Response
    """
    is_prod = _is_production()
    
    # Clear access token
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=is_prod,
        samesite=COOKIE_SAMESITE_ACCESS,
        path=COOKIE_PATH,
    )
    
    # Clear refresh token
    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        httponly=True,
        secure=is_prod,
        samesite=COOKIE_SAMESITE_REFRESH,
        path=COOKIE_PATH,
    )
    
    # Also clear legacy cookies for clean transition
    response.set_cookie(
        key="auth_token",
        value="",
        max_age=0,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        path=COOKIE_PATH,
    )
    
    response.set_cookie(
        key="discord_user_id",
        value="",
        max_age=0,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path=COOKIE_PATH,
    )
    
    logger.debug("[Auth] Cleared auth cookies")


def get_cookie_settings() -> Dict[str, Any]:
    """
    Get cookie settings for frontend reference.
    
    Returns dict with cookie configuration (no secrets).
    """
    return {
        "access_token_lifetime": ACCESS_TOKEN_LIFETIME_SECONDS,
        "refresh_token_lifetime": REFRESH_TOKEN_LIFETIME_SECONDS,
        "cookie_path": COOKIE_PATH,
        "samesite_access": COOKIE_SAMESITE_ACCESS,
        "samesite_refresh": COOKIE_SAMESITE_REFRESH,
    }
