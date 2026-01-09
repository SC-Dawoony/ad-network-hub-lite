"""AppLovin API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import sys
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class AppLovinAPI(BaseNetworkAPI):
    """AppLovin API implementation"""
    
    def __init__(self):
        super().__init__("AppLovin")
        self.api_key = get_env_var("APPLOVIN_API_KEY")
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get AppLovin API headers with authentication
        
        Returns:
            Headers dictionary or None if credentials are missing
        """
        if not self.api_key:
            return None
        
        return {
            "Accept": "application/json",
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via AppLovin API
        
        Note: AppLovin does not support app creation via API
        
        Args:
            payload: App creation payload
            
        Returns:
            API response dict with error status
        """
        return {
            "status": 1,
            "code": "NOT_SUPPORTED",
            "msg": "AppLovin does not support app creation via API"
        }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create ad unit via AppLovin API
        
        API: POST https://o.applovin.com/mediation/v1/ad_unit
        
        Args:
            payload: Unit creation payload with name, platform, package_name, ad_format
            app_key: Not used for AppLovin (kept for interface compatibility)
            
        Returns:
            API response dict
        """
        if not self.api_key:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "APPLOVIN_API_KEY must be set in .env file or Streamlit secrets"
            }
        
        url = "https://o.applovin.com/mediation/v1/ad_unit"
        headers = self._get_headers()
        
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "APPLOVIN_API_KEY must be set in .env file or Streamlit secrets"
            }
        
        logger.info(f"[AppLovin] API Request: POST {url}")
        logger.info(f"[AppLovin] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[AppLovin] Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"[AppLovin] Response Status: {response.status_code}")
            
            # Handle empty response
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"[AppLovin] Empty response body (status {response.status_code})")
                return {
                    "status": 1,
                    "code": "EMPTY_RESPONSE",
                    "msg": "Empty response from API"
                }
            
            try:
                result = response.json()
                logger.info(f"[AppLovin] Response Body: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[AppLovin] JSON decode error: {str(e)}")
                logger.error(f"[AppLovin] Response text: {response_text[:500]}")
                return {
                    "status": 1,
                    "code": "JSON_ERROR",
                    "msg": f"Invalid JSON response: {str(e)}"
                }
            
            if response.status_code == 200:
                # Success response
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Error response
                error_msg = result.get("message") or result.get("msg") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[AppLovin] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[AppLovin] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[AppLovin] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from AppLovin API
        
        Note: AppLovin does not support app listing via API
        
        Args:
            app_key: Not used for AppLovin (kept for interface compatibility)
            
        Returns:
            Empty list (AppLovin does not support app listing)
        """
        # AppLovin does not support app creation/listing via API
        return []