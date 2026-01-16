"""Base Service class for business logic"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for service layer implementations
    
    Services contain business logic and orchestrate API calls.
    They are independent of UI and can be reused across different UI components.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute the service operation
        
        Returns:
            Dict with operation result
        """
        pass

