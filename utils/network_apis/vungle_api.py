"""Vungle (Liftoff) API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class VungleAPI(BaseNetworkAPI):
    """Vungle (Liftoff) API implementation"""
    
    def __init__(self):
        super().__init__("Vungle")
        self.base_url = "https://publisher-api.vungle.com/api/v1"
    
    def _get_jwt_token(self) -> Optional[str]:
        """Get Vungle JWT Token for API calls
        
        API: GET https://auth-api.vungle.com/v2/auth
        Header: x-api-key: [secret_token]
        
        Returns:
            JWT Token string or None
        """
        # Check for existing JWT token in environment
        jwt_token = get_env_var("LIFTOFF_JWT_TOKEN") or get_env_var("VUNGLE_JWT_TOKEN")
        if jwt_token:
            logger.info("[Vungle] Using existing JWT token from environment")
            return jwt_token
        
        # Get secret token
        secret_token = get_env_var("LIFTOFF_SECRET_TOKEN") or get_env_var("VUNGLE_SECRET_TOKEN")
        if not secret_token:
            logger.error("[Vungle] LIFTOFF_SECRET_TOKEN or VUNGLE_SECRET_TOKEN not found")
            return None
        
        # Request new JWT token
        auth_url = "https://auth-api.vungle.com/v2/auth"
        headers = {
            "x-api-key": secret_token
        }
        
        logger.info(f"[Vungle] Requesting JWT token from {auth_url}")
        
        try:
            response = requests.get(auth_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("token")
                if token:
                    logger.info("[Vungle] Successfully obtained JWT token")
                    return token
                else:
                    logger.error(f"[Vungle] Token not found in response: {result}")
                    return None
            else:
                logger.error(f"[Vungle] Failed to get JWT token: {response.status_code} - {response.text[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[Vungle] Error getting JWT token: {str(e)}")
            return None
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get Vungle API headers with JWT token"""
        jwt_token = self._get_jwt_token()
        if not jwt_token:
            return None
        
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via Vungle API
        
        API: POST https://publisher-api.vungle.com/api/v1/applications
        
        Args:
            payload: App creation payload
                {
                    "platform": "ios" | "android",
                    "name": "app_name",
                    "store": {
                        "id": "string",
                        "category": "Games",
                        "isPaid": false,
                        "isManual": false,
                        "url": "string",
                        "thumbnail": "string" (optional)
                    },
                    "isCoppa": true
                }
            
        Returns:
            API response dict
        """
        url = f"{self.base_url}/applications"
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Vungle JWT token. Please check LIFTOFF_SECRET_TOKEN or VUNGLE_SECRET_TOKEN in .env file or Streamlit secrets."
            }
        
        self.logger.info(f"[Vungle] API Request: POST {url}")
        self.logger.info(f"[Vungle] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Vungle] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            # Log response
            self.logger.info(f"[Vungle] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[Vungle] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[Vungle] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Normalize response
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg,
                    "result": result
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Vungle] API Error: {str(e)}")
            return {
                "status": 1,
                "code": "REQUEST_ERROR",
                "msg": f"Request failed: {str(e)}",
                "result": {}
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (placement) via Vungle API
        
        API: POST https://publisher-api.vungle.com/api/v1/placements
        
        Args:
            payload: Placement creation payload
                {
                    "application": "vungleAppId",
                    "name": "placement_name",
                    "type": "rewarded" | "interstitial" | "banner",
                    "allowEndCards": true,
                    "isHBParticipation": true
                }
            app_key: Not used for Vungle (application is in payload)
            
        Returns:
            API response dict
        """
        url = f"{self.base_url}/placements"
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Vungle JWT token. Please check LIFTOFF_SECRET_TOKEN or VUNGLE_SECRET_TOKEN in .env file or Streamlit secrets."
            }
        
        self.logger.info(f"[Vungle] API Request: POST {url}")
        self.logger.info(f"[Vungle] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Vungle] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            # Log response
            self.logger.info(f"[Vungle] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[Vungle] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[Vungle] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Normalize response
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg,
                    "result": result
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Vungle] API Error: {str(e)}")
            return {
                "status": 1,
                "code": "REQUEST_ERROR",
                "msg": f"Request failed: {str(e)}",
                "result": {}
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from Vungle API
        
        Note: This is implemented in network_manager._get_vungle_applications()
        This method can be implemented here if needed for consistency
        """
        # For now, return empty list as it's handled by network_manager
        return []
    
    def get_units(self, app_code: str) -> List[Dict]:
        """Get units list for an app
        
        TODO: Implement when needed
        """
        return []

