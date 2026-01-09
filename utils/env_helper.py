"""Helper function to get environment variables from Streamlit secrets or .env file

DEPRECATED: Use utils.helpers.get_env_var instead
This file is kept for backward compatibility only and will be removed in future versions.
"""
import warnings
from utils.helpers import get_env_var as _get_env_var

def get_env_var(key: str, default=None):
    """Get environment variable (DEPRECATED - use utils.helpers.get_env_var)
    
    This is a compatibility wrapper. New code should use utils.helpers.get_env_var directly.
    """
    warnings.warn(
        "utils.env_helper.get_env_var is deprecated. Use utils.helpers.get_env_var instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_env_var(key, default)