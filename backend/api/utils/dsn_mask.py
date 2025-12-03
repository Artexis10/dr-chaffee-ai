"""
DSN Password Masking Utility

Masks passwords in database connection strings for safe logging.
Supports PostgreSQL, MySQL, and generic DSN formats.
"""

import re
from typing import Optional
from urllib.parse import urlparse, urlunparse


def mask_dsn_password(dsn: Optional[str], mask: str = "****") -> str:
    """
    Mask the password in a database connection string.
    
    Supports formats:
    - postgres://user:password@host:port/dbname
    - postgresql://user:password@host:port/dbname
    - mysql://user:password@host:port/dbname
    - Any URL-style DSN with user:password@host
    
    Args:
        dsn: Database connection string (may be None)
        mask: String to replace password with (default: "****")
        
    Returns:
        DSN with password masked, or empty string if dsn is None/empty
        
    Examples:
        >>> mask_dsn_password("postgres://user:secret@localhost:5432/db")
        'postgres://user:****@localhost:5432/db'
        
        >>> mask_dsn_password(None)
        ''
    """
    if not dsn:
        return ""
    
    try:
        parsed = urlparse(dsn)
        
        # If there's a password, mask it
        if parsed.password:
            # Reconstruct netloc with masked password
            if parsed.port:
                masked_netloc = f"{parsed.username}:{mask}@{parsed.hostname}:{parsed.port}"
            else:
                masked_netloc = f"{parsed.username}:{mask}@{parsed.hostname}"
            
            # Reconstruct the full URL
            masked = urlunparse((
                parsed.scheme,
                masked_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return masked
        
        # No password to mask
        return dsn
        
    except Exception:
        # Fallback: use regex for edge cases
        # Pattern: scheme://user:password@host
        pattern = r'(://[^:]+:)([^@]+)(@)'
        return re.sub(pattern, rf'\1{mask}\3', dsn)


def mask_env_dsn(env_var_name: str = "DATABASE_URL", mask: str = "****") -> str:
    """
    Get and mask a DSN from environment variable.
    
    Args:
        env_var_name: Name of environment variable containing DSN
        mask: String to replace password with
        
    Returns:
        Masked DSN or "not set" if env var is empty
    """
    import os
    dsn = os.getenv(env_var_name, "")
    if not dsn:
        return "not set"
    return mask_dsn_password(dsn, mask)
