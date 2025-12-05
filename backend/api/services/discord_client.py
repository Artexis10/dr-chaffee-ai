"""
Discord OAuth Client Service

Provides helper functions for Discord OAuth2 authentication flow:
- Building authorization URLs
- Exchanging authorization codes for tokens
- Fetching user information
- Checking guild membership and roles

Uses per-user membership check approach (guilds.members.read scope),
NOT global member syncing.
"""

import os
import secrets
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# Discord API endpoints
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_AUTHORIZE = "https://discord.com/oauth2/authorize"
DISCORD_OAUTH_TOKEN = f"{DISCORD_API_BASE}/oauth2/token"

# Request timeout for Discord API calls (seconds)
DISCORD_API_TIMEOUT = 10.0


class DiscordConfig:
    """
    Discord OAuth configuration from environment variables.
    
    Required env vars:
        DISCORD_CLIENT_ID          - OAuth2 client ID from Discord Developer Portal
        DISCORD_CLIENT_SECRET      - OAuth2 client secret
        DISCORD_REDIRECT_URI       - Callback URL registered in Discord app
                                     Dev:  http://localhost:8000/auth/discord/callback
                                     Prod: https://app.askdrchaffee.com/api/auth/discord/callback
                                     MUST match exactly what's in Discord Developer Portal!
        DISCORD_GUILD_ID           - Server ID users must be a member of
        DISCORD_ALLOWED_ROLE_IDS   - Comma-separated role IDs that grant access
    
    Optional env vars:
        DISCORD_OAUTH_SCOPES       - OAuth scopes (default: identify guilds guilds.members.read)
        FRONTEND_APP_URL           - Where to redirect after auth (default: http://localhost:3000)
    """
    
    # Default scopes: identify (user info), guilds (list guilds), guilds.members.read (role check)
    DEFAULT_SCOPES = "identify guilds guilds.members.read"
    
    def __init__(self):
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("DISCORD_REDIRECT_URI", "")
        self.guild_id = os.getenv("DISCORD_GUILD_ID", "")
        self.scopes = os.getenv("DISCORD_OAUTH_SCOPES", self.DEFAULT_SCOPES)
        self.frontend_url = os.getenv("FRONTEND_APP_URL", "http://localhost:3000")
        
        # Parse allowed role IDs from comma-separated string
        role_ids_str = os.getenv("DISCORD_ALLOWED_ROLE_IDS", "")
        self.allowed_role_ids: List[str] = [
            rid.strip() for rid in role_ids_str.split(",") if rid.strip()
        ]
        
        # Convert to set for O(1) membership checks
        self.allowed_role_ids_set: set = set(self.allowed_role_ids)
    
    def is_configured(self) -> bool:
        """Check if Discord OAuth is properly configured."""
        return bool(
            self.client_id and 
            self.client_secret and 
            self.redirect_uri and 
            self.guild_id and
            self.allowed_role_ids
        )
    
    def get_missing_config(self) -> List[str]:
        """Return list of missing configuration items."""
        missing = []
        if not self.client_id:
            missing.append("DISCORD_CLIENT_ID")
        if not self.client_secret:
            missing.append("DISCORD_CLIENT_SECRET")
        if not self.redirect_uri:
            missing.append("DISCORD_REDIRECT_URI")
        if not self.guild_id:
            missing.append("DISCORD_GUILD_ID")
        if not self.allowed_role_ids:
            missing.append("DISCORD_ALLOWED_ROLE_IDS")
        return missing


# Global config instance
_config: Optional[DiscordConfig] = None


def get_discord_config() -> DiscordConfig:
    """Get Discord configuration (singleton)."""
    global _config
    if _config is None:
        _config = DiscordConfig()
    return _config


def generate_state_token() -> str:
    """Generate a secure random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def build_discord_authorize_url(state: str) -> str:
    """
    Build the Discord OAuth2 authorization URL.
    
    Args:
        state: CSRF protection state token
        
    Returns:
        Full authorization URL to redirect user to
        
    Raises:
        ValueError: If DISCORD_REDIRECT_URI is not configured
    """
    config = get_discord_config()
    
    # Validate redirect_uri is set
    if not config.redirect_uri:
        logger.error("DISCORD_REDIRECT_URI is not set! Cannot build OAuth URL.")
        raise ValueError("DISCORD_REDIRECT_URI environment variable is required")
    
    # Log the redirect_uri being used (helps debug mismatches)
    logger.info(f"Building Discord OAuth URL with redirect_uri: {config.redirect_uri}")
    
    # Warn if redirect_uri looks like localhost in production
    if "localhost" in config.redirect_uri and os.getenv("NODE_ENV") == "production":
        logger.warning(
            f"DISCORD_REDIRECT_URI contains 'localhost' but NODE_ENV=production. "
            f"This will likely cause OAuth failures. Current value: {config.redirect_uri}"
        )
    
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scopes,
        "state": state,
        "prompt": "consent",
    }
    
    return f"{DISCORD_OAUTH_AUTHORIZE}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from Discord callback
        
    Returns:
        Token response dict with access_token, or None on failure
    """
    config = get_discord_config()
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri,
    }
    
    # Use HTTP Basic auth as recommended by Discord
    auth = (config.client_id, config.client_secret)
    
    logger.info("Exchanging authorization code for access token")
    
    try:
        async with httpx.AsyncClient(timeout=DISCORD_API_TIMEOUT) as client:
            response = await client.post(
                DISCORD_OAUTH_TOKEN,
                data=data,
                auth=auth,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code == 200:
                logger.info("Token exchange successful")
                return response.json()
            else:
                # Don't log response body - may contain sensitive info
                logger.error(f"Discord token exchange failed: HTTP {response.status_code}")
                return None
                
    except httpx.TimeoutException:
        logger.error("Discord token exchange timed out")
        return None
    except httpx.RequestError as e:
        logger.error(f"Discord token exchange request failed: {type(e).__name__}")
        return None


async def get_discord_user(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the authenticated user's Discord profile.
    
    Args:
        access_token: OAuth access token
        
    Returns:
        User object with id, username, discriminator, global_name, avatar
    """
    try:
        async with httpx.AsyncClient(timeout=DISCORD_API_TIMEOUT) as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                user = response.json()
                # Log only non-sensitive identifier (last 6 chars of Discord ID)
                user_id = user.get("id", "")
                logger.info(f"Fetched Discord user: ...{user_id[-6:]}")
                return user
            else:
                logger.error(f"Discord get user failed: HTTP {response.status_code}")
                return None
                
    except httpx.TimeoutException:
        logger.error("Discord get user timed out")
        return None
    except httpx.RequestError as e:
        logger.error(f"Discord get user request failed: {type(e).__name__}")
        return None


async def get_guild_member(access_token: str, guild_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the user's membership info for a specific guild.
    
    Uses the /users/@me/guilds/{guild_id}/member endpoint which requires
    the guilds.members.read scope.
    
    Args:
        access_token: OAuth access token
        guild_id: Discord guild (server) ID
        
    Returns:
        Member object with roles array, or None if not a member
    """
    # Log only last 6 chars of guild ID for privacy
    logger.info(f"Checking guild membership for guild ...{guild_id[-6:]}")
    
    try:
        async with httpx.AsyncClient(timeout=DISCORD_API_TIMEOUT) as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me/guilds/{guild_id}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                member = response.json()
                role_count = len(member.get("roles", []))
                logger.info(f"User is guild member with {role_count} roles")
                return member
            elif response.status_code == 404:
                # User is not a member of this guild
                logger.info("User is not a member of the required guild")
                return None
            else:
                logger.error(f"Discord get guild member failed: HTTP {response.status_code}")
                return None
                
    except httpx.TimeoutException:
        logger.error("Discord get guild member timed out")
        return None
    except httpx.RequestError as e:
        logger.error(f"Discord get guild member request failed: {type(e).__name__}")
        return None


def user_has_allowed_role(member: Dict[str, Any], allowed_role_ids: List[str]) -> bool:
    """
    Check if the guild member has at least one of the allowed roles.
    
    Args:
        member: Guild member object from Discord API
        allowed_role_ids: List of role IDs that grant access
        
    Returns:
        True if user has at least one allowed role
    """
    if not member or not allowed_role_ids:
        logger.info("Role check failed: no member or no allowed roles configured")
        return False
    
    user_roles = set(member.get("roles", []))
    allowed_set = set(allowed_role_ids)
    
    # Check intersection
    matching_roles = user_roles & allowed_set
    
    if matching_roles:
        logger.info(f"User has {len(matching_roles)} matching role(s) - access granted")
        return True
    
    logger.info(f"User has {len(user_roles)} roles but none match the {len(allowed_set)} allowed roles")
    return False


class DiscordAuthError(Exception):
    """Base exception for Discord auth errors."""
    pass


class NotInGuildError(DiscordAuthError):
    """User is not a member of the required guild."""
    pass


class InsufficientRoleError(DiscordAuthError):
    """User is in guild but lacks required roles."""
    pass


class DiscordAPIError(DiscordAuthError):
    """Discord API request failed."""
    pass
