"""
Discord Roles → Tier Mapping Loader

Provides cached loading and resolution of Discord role IDs to membership tiers.
Configuration is stored in backend/config/discord_roles.json.

Usage:
    from .discord_roles_loader import resolve_user_tier, get_tier_label, resolve_user_tier_with_info

    tier = resolve_user_tier(["1011035139658231949", "1005862311027814521"])
    # Returns: "paragon_of_virtue" (highest priority tier)

    label = get_tier_label("paragon_of_virtue")
    # Returns: "Paragon of Virtue"

    tier_info = resolve_user_tier_with_info(["1011035139658231949"])
    # Returns: {"tier": "paragon_of_virtue", "name": "Paragon of Virtue", "color": "#C27C0E"}
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Path to the JSON config file
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "discord_roles.json"
)


@lru_cache(maxsize=1)
def _load_config() -> Optional[Dict[str, Any]]:
    """
    Load and cache the discord_roles.json configuration.
    
    Returns:
        Parsed JSON config dict, or None if loading fails.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"Loaded Discord roles config from {CONFIG_PATH}")
            return config
    except FileNotFoundError:
        logger.warning(f"Discord roles config not found: {CONFIG_PATH}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Discord roles config: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load Discord roles config: {e}")
        return None


def get_role_config() -> Dict[str, Dict[str, str]]:
    """
    Get the role ID → tier mapping.
    
    Returns:
        Dict mapping role IDs to {"tier": "...", "name": "..."}, or empty dict on error.
    """
    config = _load_config()
    if not config:
        return {}
    return config.get("roles", {})


def get_tier_priority() -> List[str]:
    """
    Get the tier priority list (highest priority first).
    
    Returns:
        List of tier IDs in priority order, or empty list on error.
    """
    config = _load_config()
    if not config:
        return []
    return config.get("tiers_priority", [])


def get_all_tiers() -> List[Dict[str, str]]:
    """
    Get all tiers with their IDs, names, and colors for API exposure.
    
    Returns:
        List of {"id": "tier_id", "name": "Tier Name", "color": "#HEXCODE"} in priority order.
    """
    config = _load_config()
    if not config:
        return []
    
    roles = config.get("roles", {})
    priority = config.get("tiers_priority", [])
    
    # Build tier info from roles, ordered by priority
    # Store as dict: tier_id -> {name, color}
    tier_info: Dict[str, Dict[str, str]] = {}
    for role_data in roles.values():
        tier_id = role_data.get("tier")
        tier_name = role_data.get("name")
        tier_color = role_data.get("color", "#444444")
        if tier_id and tier_name:
            tier_info[tier_id] = {"name": tier_name, "color": tier_color}
    
    # Return in priority order
    result = []
    for tier_id in priority:
        if tier_id in tier_info:
            result.append({
                "id": tier_id,
                "name": tier_info[tier_id]["name"],
                "color": tier_info[tier_id]["color"]
            })
    
    return result


def get_tier_label(tier_id: Optional[str]) -> Optional[str]:
    """
    Get the human-readable label for a tier ID.
    
    Args:
        tier_id: The machine tier ID (e.g., "vip")
        
    Returns:
        Human-readable name (e.g., "VIP"), or None if not found.
    """
    if not tier_id:
        return None
    
    roles = get_role_config()
    for role_data in roles.values():
        if role_data.get("tier") == tier_id:
            return role_data.get("name")
    
    return None


def resolve_user_tier(user_role_ids: List[str]) -> Optional[str]:
    """
    Resolve a user's Discord roles to their highest-priority tier.
    
    Args:
        user_role_ids: List of Discord role IDs the user has.
        
    Returns:
        The tier ID of the highest-priority matching tier, or None if no match.
        
    Example:
        >>> resolve_user_tier(["1011035139658231949", "1005862311027814521"])
        "paragon_of_virtue"  # Highest priority of the two
    """
    if not user_role_ids:
        return None
    
    roles = get_role_config()
    priority = get_tier_priority()
    
    if not roles or not priority:
        logger.warning("Discord roles config not loaded, cannot resolve tier")
        return None
    
    # Map user's role IDs to tier IDs
    user_tiers = set()
    for role_id in user_role_ids:
        role_id_str = str(role_id)  # Ensure string comparison
        if role_id_str in roles:
            tier = roles[role_id_str].get("tier")
            if tier:
                user_tiers.add(tier)
    
    if not user_tiers:
        logger.debug(f"No matching tiers for roles: {user_role_ids}")
        return None
    
    # Return highest priority tier
    for tier in priority:
        if tier in user_tiers:
            logger.debug(f"Resolved tier: {tier} from roles: {user_role_ids}")
            return tier
    
    # Fallback: return any matched tier (shouldn't happen if config is correct)
    return next(iter(user_tiers))


def get_tier_info(tier_id: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Get full tier info (tier, name, color) for a tier ID.
    
    Args:
        tier_id: The machine tier ID (e.g., "vip")
        
    Returns:
        Dict with {"tier": "...", "name": "...", "color": "..."}, or None if not found.
    """
    if not tier_id:
        return None
    
    roles = get_role_config()
    for role_data in roles.values():
        if role_data.get("tier") == tier_id:
            return {
                "tier": tier_id,
                "name": role_data.get("name", ""),
                "color": role_data.get("color", "#444444")
            }
    
    return None


def get_tier_color(tier_id: Optional[str]) -> Optional[str]:
    """
    Get the color for a tier ID.
    
    Args:
        tier_id: The machine tier ID (e.g., "vip")
        
    Returns:
        Hex color string (e.g., "#95A5A6"), or None if not found.
    """
    info = get_tier_info(tier_id)
    return info.get("color") if info else None


def resolve_user_tier_with_info(user_role_ids: List[str]) -> Optional[Dict[str, str]]:
    """
    Resolve a user's Discord roles to their highest-priority tier with full info.
    
    Args:
        user_role_ids: List of Discord role IDs the user has.
        
    Returns:
        Dict with {"tier": "...", "name": "...", "color": "..."}, or None if no match.
        
    Example:
        >>> resolve_user_tier_with_info(["1011035139658231949"])
        {"tier": "paragon_of_virtue", "name": "Paragon of Virtue", "color": "#C27C0E"}
    """
    tier_id = resolve_user_tier(user_role_ids)
    if not tier_id:
        return None
    return get_tier_info(tier_id)


def clear_cache() -> None:
    """
    Clear the cached config. Useful for testing or hot-reloading.
    """
    _load_config.cache_clear()
    logger.info("Discord roles config cache cleared")
