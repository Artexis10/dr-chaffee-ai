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


class DiscordConfig:
    """Discord OAuth configuration from environment variables."""
    
    def __init__(self):
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("DISCORD_REDIRECT_URI", "")
        self.guild_id = os.getenv("DISCORD_GUILD_ID", "")
        self.scopes = os.getenv("DISCORD_OAUTH_SCOPES", "identify guilds.members.read")
        self.frontend_url = os.getenv("FRONTEND_APP_URL", "http://localhost:3000")
        
        # Parse allowed role IDs from comma-separated string
        role_ids_str = os.getenv("DISCORD_ALLOWED_ROLE_IDS", "")
        self.allowed_role_ids: List[str] = [
            rid.strip() for rid in role_ids_str.split(",") if rid.strip()
        ]
    
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
    """
    config = get_discord_config()
    
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
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DISCORD_OAUTH_TOKEN,
                data=data,
                auth=auth,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Discord token exchange failed: {response.status_code} - {response.text}"
                )
                return None
                
    except httpx.RequestError as e:
        logger.error(f"Discord token exchange request failed: {e}")
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Discord get user failed: {response.status_code} - {response.text}"
                )
                return None
                
    except httpx.RequestError as e:
        logger.error(f"Discord get user request failed: {e}")
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
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me/guilds/{guild_id}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # User is not a member of this guild
                logger.info(f"User is not a member of guild {guild_id}")
                return None
            else:
                logger.error(
                    f"Discord get guild member failed: {response.status_code} - {response.text}"
                )
                return None
                
    except httpx.RequestError as e:
        logger.error(f"Discord get guild member request failed: {e}")
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
        return False
    
    user_roles = member.get("roles", [])
    
    for role_id in allowed_role_ids:
        if role_id in user_roles:
            return True
    
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
