"""Base class for network API implementations"""
from typing import Dict, List, Optional
import requests
import json
import logging
from abc import ABC, abstractmethod
from utils.helpers import mask_sensitive_data

logger = logging.getLogger(__name__)

class BaseNetworkAPI(ABC):
    """Base class for network API implementations"""
    
    def __init__(self, network_name: str):
        self.network_name = network_name
        self.logger = logging.getLogger(f"{__name__}.{network_name}")
    
    @abstractmethod
    def create_app(self, payload: Dict) -> Dict:
        """Create app via network API
        
        Args:
            payload: App creation payload
            
        Returns:
            API response dict
        """
        pass
    
    @abstractmethod
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (placement/ad unit) via network API
        
        Args:
            payload: Unit creation payload
            app_key: Optional app key/ID
            
        Returns:
            API response dict
        """
        pass
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from network
        
        Args:
            app_key: Optional app key to filter by
            
        Returns:
            List of app dicts
        """
        # Default implementation returns empty list
        # Override in subclasses if network supports app listing
        return []
    
    def get_units(self, app_code: str) -> List[Dict]:
        """Get units list for an app
        
        Args:
            app_code: App code/ID
            
        Returns:
            List of unit dicts
        """
        # Default implementation returns empty list
        # Override in subclasses if network supports unit listing
        return []
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> requests.Response:
        """Make HTTP request with error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            url: Request URL
            headers: Request headers
            data: Form data
            json_data: JSON data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            requests.Response object
        """
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == "POST":
                if json_data:
                    response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
                elif data:
                    response = requests.post(url, headers=headers, data=data, timeout=timeout)
                else:
                    response = requests.post(url, headers=headers, timeout=timeout)
            elif method.upper() == "PUT":
                if json_data:
                    response = requests.put(url, headers=headers, json=json_data, timeout=timeout)
                elif data:
                    response = requests.put(url, headers=headers, data=data, timeout=timeout)
                else:
                    response = requests.put(url, headers=headers, timeout=timeout)
            elif method.upper() == "PATCH":
                if json_data:
                    response = requests.patch(url, headers=headers, json=json_data, timeout=timeout)
                elif data:
                    response = requests.patch(url, headers=headers, data=data, timeout=timeout)
                else:
                    response = requests.patch(url, headers=headers, timeout=timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[{self.network_name}] Request failed: {str(e)}")
            raise

