# utils/network_apis/fyber_api.py
"""Fyber API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class FyberAPI(BaseNetworkAPI):
    """Fyber (DT) API implementation"""
    
    def __init__(self):
        super().__init__("Fyber")
        self.client_id_raw = get_env_var("DT_CLIENT_ID") or get_env_var("FYBER_CLIENT_ID")
        self.client_secret_raw = get_env_var("DT_CLIENT_SECRET") or get_env_var("FYBER_CLIENT_SECRET")
        self.client_id = self.client_id_raw.strip() if self.client_id_raw else None
        self.client_secret = self.client_secret_raw.strip() if self.client_secret_raw else None
    
    def _get_access_token(self) -> Optional[str]:
        """Get Fyber (DT) Access Token
        
        Always fetches a new access token using DT_CLIENT_ID and DT_CLIENT_SECRET.
        API: POST https://console.fyber.com/api/v2/management/auth
        Payload: grant_type, client_id, client_secret
        """
        if not self.client_id or not self.client_secret:
            self.logger.error("[Fyber] DT_CLIENT_ID and DT_CLIENT_SECRET must be set")
            self.logger.error(f"[Fyber] client_id is None or empty: {not self.client_id}, client_secret is None or empty: {not self.client_secret}")
            self.logger.error(f"[Fyber] Please check:")
            self.logger.error(f"[Fyber]   1. .env file has DT_CLIENT_ID and DT_CLIENT_SECRET (or FYBER_CLIENT_ID and FYBER_CLIENT_SECRET)")
            self.logger.error(f"[Fyber]   2. Streamlit secrets has DT_CLIENT_ID and DT_CLIENT_SECRET")
            self.logger.error(f"[Fyber]   3. Values are not empty or whitespace-only")
            return None
        
        auth_url = "https://console.fyber.com/api/v2/management/auth"
        
        payload = {
            "grant_type": "management_client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        self.logger.info(f"[Fyber] Requesting new access token from: {auth_url}")
        self.logger.info(f"[Fyber] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", auth_url, headers=headers, json_data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # Check both accessToken and access_token (API may return either)
                access_token = result.get("accessToken") or result.get("access_token")
                if access_token:
                    self.logger.info(f"[Fyber] ✅ Successfully obtained new access token (length: {len(access_token)})")
                    return access_token
                else:
                    self.logger.error(f"[Fyber] ❌ Access token not found in response: {result}")
                    return None
            else:
                self.logger.error(f"[Fyber] ❌ Failed to get access token. Status: {response.status_code}")
                self.logger.error(f"[Fyber] Response: {response.text}")
                
                # Provide helpful error messages
                if "invalid_client" in response.text:
                    self.logger.error("[Fyber] 💡 'invalid_client' 오류:")
                    self.logger.error("[Fyber]   → Client ID 또는 Client Secret이 올바르지 않습니다.")
                    self.logger.error("[Fyber]   → Fyber Console > Settings > API Credentials > Management API")
                    self.logger.error("[Fyber]   → UI에서 받은 Client ID와 Client Secret을 정확히 복사했는지 확인")
                elif "invalid_request" in response.text:
                    self.logger.error("[Fyber] 💡 'invalid_request' 오류:")
                    self.logger.error("[Fyber]   → 요청 파라미터가 올바르지 않습니다.")
                    self.logger.error("[Fyber]   → grant_type이 'management_client_credentials'인지 확인")
                
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Fyber] ❌ API Error (Get Access Token): {str(e)}")
            return None
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get Fyber API headers with Bearer token"""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via Fyber (DT) API"""
        url = "https://console.fyber.com/api/management/v1/app"
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        self.logger.info(f"[Fyber] API Request: POST {url}")
        self.logger.info(f"[Fyber] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Fyber] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            # Log response even if status code is not 200
            self.logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[Fyber] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Fyber API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # Provide helpful error messages for common errors
                if response.status_code == 409:
                    if "Invalid store category1" in error_msg:
                        self.logger.error("[Fyber] 💡 카테고리 오류:")
                        self.logger.error("[Fyber]   → 선택한 카테고리가 플랫폼에 맞지 않습니다.")
                        self.logger.error("[Fyber]   → Android와 iOS는 서로 다른 카테고리를 사용합니다.")
                        self.logger.error(f"[Fyber]   → 에러 메시지: {error_msg[:200]}...")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Fyber] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create placement (unit) via Fyber (DT) API
        
        Note: Fyber uses 'appId' in payload (as string), not app_key parameter.
        The app_key parameter is accepted for interface consistency but is not used.
        
        Args:
            payload: Unit creation payload (must include 'appId' field as string)
            app_key: Not used (for interface consistency only)
        """
        url = "https://console.fyber.com/api/management/v1/placement"
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        # If payload doesn't have appId and app_key is provided, use it as fallback
        if "appId" not in payload and app_key:
            # Fyber expects appId as string
            payload["appId"] = str(app_key)
        
        self.logger.info(f"[Fyber] API Request: POST {url}")
        self.logger.info(f"[Fyber] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Fyber] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            # Log response even if status code is not 200
            self.logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[Fyber] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Fyber API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Fyber] API Error (Create Placement): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from Fyber (DT) API
        
        API: GET https://console.fyber.com/api/management/v1/app?publisherId={publisherId}
        or GET https://console.fyber.com/api/management/v1/app?appId={appId}
        
        Note: Fyber uses publisher_id or app_id as query parameters, not app_key.
        The app_key parameter can be parsed to extract app_id.
        
        Args:
            app_key: Optional app key (can be "app:123" format or numeric string)
                     If provided, will be parsed as app_id
        """
        # Get access token
        access_token = self._get_access_token()
        if not access_token:
            self.logger.error("[Fyber] Failed to get access token for get_apps")
            return []
        
        # Parse app_key to get publisher_id or app_id
        publisher_id = None
        app_id = None
        
        if app_key:
            try:
                if app_key.startswith("app:"):
                    app_id = int(app_key.split(":")[1])
                else:
                    # Try as app_id first (more specific)
                    numeric_value = int(app_key)
                    app_id = numeric_value
            except ValueError:
                self.logger.warning(f"[Fyber] Invalid app_key format: {app_key}")
        
        # If not provided in app_key, try environment variables
        if not publisher_id and not app_id:
            publisher_id_str = get_env_var("FYBER_PUBLISHER_ID") or get_env_var("DT_PUBLISHER_ID")
            app_id_str = get_env_var("FYBER_APP_ID") or get_env_var("DT_APP_ID")
            
            if app_id_str:
                try:
                    app_id = int(app_id_str)
                except ValueError:
                    self.logger.warning(f"[Fyber] Invalid FYBER_APP_ID: {app_id_str}")
            elif publisher_id_str:
                try:
                    publisher_id = int(publisher_id_str)
                except ValueError:
                    self.logger.warning(f"[Fyber] Invalid FYBER_PUBLISHER_ID: {publisher_id_str}")
        
        if not publisher_id and not app_id:
            self.logger.error("[Fyber] publisher_id or app_id is required for get_apps")
            return []
        
        url = "https://console.fyber.com/api/management/v1/app"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {}
        if publisher_id:
            params["publisherId"] = publisher_id
        if app_id:
            params["appId"] = app_id
        
        self.logger.info(f"[Fyber] Get Apps API Request: GET {url}")
        self.logger.info(f"[Fyber] Params: {json.dumps(params, indent=2)}")
        
        try:
            response = self._make_request("GET", url, headers=headers, params=params, timeout=30)
            
            self.logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
                
                # Parse response - can be list or dict
                apps = []
                if isinstance(result, list):
                    apps = result
                elif isinstance(result, dict):
                    # Check if it's a single app object (has appId or id field)
                    if "appId" in result or "id" in result:
                        # Single app object
                        apps = [result]
                    else:
                        # Dict with apps array
                        apps = result.get("apps", result.get("data", result.get("list", [])))
                        if not isinstance(apps, list):
                            # If still not a list, treat as single app
                            apps = [result]
                
                # Convert to standard format
                formatted_apps = []
                for app in apps:
                    # Fyber API returns appId as string or number
                    app_id_val = app.get("appId") or app.get("id")
                    # Convert to string if it's a number, keep as string if already string
                    if app_id_val is not None:
                        app_id_val = str(app_id_val) if not isinstance(app_id_val, str) else app_id_val
                    app_name = app.get("name") or "Unknown"
                    platform = app.get("platform", "").lower()
                    bundle_id = app.get("bundle") or app.get("bundleId") or ""
                    
                    formatted_apps.append({
                        "appCode": app_id_val if app_id_val else "N/A",
                        "appId": app_id_val if app_id_val else "N/A",
                        "id": app_id_val,  # Also keep original "id" field for compatibility
                        "name": app_name,
                        "platform": platform,
                        "status": app.get("status") or "Active",
                        "bundleId": bundle_id,
                        "bundle": bundle_id,  # Also keep "bundle" field for Fyber
                    })
                
                self.logger.info(f"[Fyber] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                error_msg = result.get("msg") or result.get("message") if "result" in locals() else "Unknown error"
                self.logger.error(f"[Fyber] API Error (Get Apps): {error_msg}")
                return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Fyber] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return []
        except Exception as e:
            self.logger.error(f"[Fyber] Unexpected Error (Get Apps): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []