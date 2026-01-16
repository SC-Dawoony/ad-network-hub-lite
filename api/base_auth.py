"""Base class for network authentication"""
from typing import Optional
import logging
from utils.helpers import get_env_var 

logger = logging.getLogger(__name__)


class BaseAuth:
    """Base class for network authentication"""
    
    def __init__(self, network_name: str):
        self.network_name = network_name
        self.logger = logging.getLogger(f"{__name__}.{network_name}")
    
    def get_env_var(self, key: str) -> Optional[str]:
        """Get environment variable"""
        return get_env_var(key)