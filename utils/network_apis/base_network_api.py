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
        """Make HTTP request with logging
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: Request URL
            headers: Request headers
            data: Request data (for form data)
            json_data: Request JSON data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        self.logger.info(f"[{self.network_name}] API Request: {method} {url}")
        
        if headers:
            self.logger.info(f"[{self.network_name}] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        
        if json_data:
            self.logger.info(f"[{self.network_name}] Request Payload: {json.dumps(mask_sensitive_data(json_data), indent=2)}")
        elif data:
            self.logger.info(f"[{self.network_name}] Request Data: {json.dumps(mask_sensitive_data(data), indent=2)}")
        
        if params:
            self.logger.info(f"[{self.network_name}] Request Params: {json.dumps(mask_sensitive_data(params), indent=2)}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                timeout=timeout
            )
            
            self.logger.info(f"[{self.network_name}] Response Status: {response.status_code}")
            
            # Check if response is empty before trying to parse JSON
            response_text = response.text.strip()
            if response_text:
                try:
                    response_data = response.json()
                    self.logger.info(f"[{self.network_name}] Response Data: {json.dumps(mask_sensitive_data(response_data), indent=2)}")
                except json.JSONDecodeError:
                    # Non-JSON response is OK, just log it
                    self.logger.warning(f"[{self.network_name}] Response is not JSON: {response_text[:500]}")
            else:
                # Empty response is OK, just log it
                self.logger.info(f"[{self.network_name}] Response is empty (status {response.status_code})")
            
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[{self.network_name}] Request Error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"[{self.network_name}] Unexpected error in _make_request: {str(e)}")
            raise
