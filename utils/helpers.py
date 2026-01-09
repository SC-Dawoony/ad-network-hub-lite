"""Common helper functions used across the application"""
import os
import json
import logging
from typing import Dict, Optional, Any, List
import streamlit as st

logger = logging.getLogger(__name__)


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable from Streamlit secrets (if available) or .env file
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and st.secrets:
            # Try direct access first
            try:
                if key in st.secrets:
                    value = st.secrets[key]
                    logger.debug(f"[Env] Found {key} in Streamlit secrets")
                    return str(value) if value is not None else default
            except (KeyError, AttributeError, TypeError):
                pass
            
            # Try using .get() method if available
            try:
                if hasattr(st.secrets, 'get'):
                    value = st.secrets.get(key)
                    if value is not None:
                        logger.debug(f"[Env] Found {key} in Streamlit secrets via .get()")
                        return str(value)
            except Exception:
                pass
            
            # Try nested access (e.g., st.secrets["ironsource"]["SECRET_KEY"])
            try:
                if isinstance(st.secrets, dict):
                    for top_level_key in st.secrets.keys():
                        try:
                            nested_dict = st.secrets[top_level_key]
                            if isinstance(nested_dict, dict) and key in nested_dict:
                                value = nested_dict[key]
                                logger.debug(f"[Env] Found {key} in Streamlit secrets[{top_level_key}]")
                                return str(value) if value is not None else default
                        except (KeyError, AttributeError, TypeError):
                            continue
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[Env] Error accessing Streamlit secrets: {str(e)}")
    
    # Fallback to environment variables (from .env file or system env)
    env_value = os.getenv(key, default)
    if env_value:
        logger.debug(f"[Env] Found {key} in environment variables")
    return env_value


def mask_sensitive_data(data: Any) -> Any:
    """Mask sensitive data in request/response for logging
    
    Args:
        data: Dict, List, or None to mask
        
    Returns:
        Masked data (same type as input)
    """
    if data is None:
        return {}
    
    # Handle list data
    if isinstance(data, list):
        return [mask_sensitive_data(item) if isinstance(item, dict) else item for item in data]
    
    # Handle dict data
    if not isinstance(data, dict):
        return data
    
    masked = data.copy()
    sensitive_keys = [
        'security_key', 'sign', 'token', 'authorization', 'bearer_token', 
        'refresh_token', 'secret_key', 'api_key', 'password', 'secret',
        'client_secret', 'x-client-secret', 'x-api-key', 'x-bigo-sign'
    ]
    
    for key in sensitive_keys:
        if key in masked:
            masked[key] = "***MASKED***"
    
    # Also mask keys that contain these words
    for key in list(masked.keys()):
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in ['token', 'key', 'secret', 'password', 'sign', 'auth']):
            if not isinstance(masked[key], (int, float)):
                masked[key] = "***MASKED***"
    
    return masked