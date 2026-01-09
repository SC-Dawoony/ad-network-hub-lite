# utils/network_apis/inmobi_api.py
"""InMobi API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import sys
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class InMobiAPI(BaseNetworkAPI):
    """InMobi API implementation"""
    
    def __init__(self):
        super().__init__("InMobi")
        self.username = get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        self.account_id = get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        self.client_secret = get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
    
    def _get_headers(self, content_type: str = "application/json") -> Optional[Dict[str, str]]:
        """Get InMobi API headers with authentication
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            Headers dictionary or None if credentials are missing
        """
        if not self.username or not self.account_id or not self.client_secret:
            return None
        
        return {
            "x-client-id": self.username,
            "x-account-id": self.account_id,
            "x-client-secret": self.client_secret,
            "Content-Type": content_type,
            "Accept": "application/json",
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        if not self.username or not self.account_id or not self.client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to generate InMobi headers"
            }
        
        # Remove None values and empty strings from payload
        cleaned_payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        
        self.logger.info(f"[InMobi] API Request: POST {url}")
        self.logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[InMobi] Request Payload: {json.dumps(mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=cleaned_payload, timeout=30)
            
            # Log response even if status code is not 200
            self.logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[InMobi] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # For 400 errors, log detailed error information
            if response.status_code == 400:
                self.logger.error(f"[InMobi] Bad Request (400) - Full Response: {response.text}")
                print(f"[InMobi] ❌ Bad Request (400)", file=sys.stderr)
                print(f"[InMobi] Response: {response.text}", file=sys.stderr)
                # Try to extract more details from error response
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, dict):
                        error_msg = error_detail.get("message") or error_detail.get("error") or error_detail.get("msg") or str(error_detail)
                        self.logger.error(f"[InMobi] Error Details: {error_msg}")
                        print(f"[InMobi] Error Details: {error_msg}", file=sys.stderr)
                except:
                    pass
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[InMobi] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                    print(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}", file=sys.stderr)
                except:
                    self.logger.error(f"[InMobi] Error Response (text): {e.response.text}")
                    print(f"[InMobi] Error Response (text): {e.response.text}", file=sys.stderr)
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (placement) via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v1/placements"
        
        if not self.username or not self.account_id or not self.client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to generate InMobi headers"
            }
        
        self.logger.info(f"[InMobi] API Request: POST {url}")
        self.logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[InMobi] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            # Log response even if status code is not 200
            self.logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                self.logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[InMobi] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or response.status_code
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[InMobi] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from InMobi API
        
        API: GET https://publisher.inmobi.com/rest/api/v2/apps
        Headers: x-client-id, x-account-id, x-client-secret
        """
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        if not self.username or not self.account_id or not self.client_secret:
            self.logger.error("[InMobi] INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set")
            return []
        
        headers = self._get_headers(content_type=None)  # GET 요청이므로 Content-Type 불필요
        if headers:
            headers.pop("Content-Type", None)  # Content-Type 제거
        
        if not headers:
            self.logger.error("[InMobi] Failed to generate headers")
            return []
        
        # Query parameters
        params = {
            "pageNum": 1,
            "pageLength": 10,
            "status": "ACTIVE",
        }
        
        self.logger.info(f"[InMobi] API Request: GET {url}")
        self.logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[InMobi] Request Params: {json.dumps(params, indent=2)}")
        
        try:
            response = self._make_request("GET", url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            try:
                result = response.json()
                self.logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                self.logger.error(f"[InMobi] Response Text: {response.text}")
                return []
            
            # InMobi API 응답 형식에 맞게 처리
            # Response format: {"data": {"records": [...], "totalRecords": ...}} or {"data": {"apps": [...]}} or {"data": [...]}
            if response.status_code == 200:
                # Extract apps from response
                if isinstance(result, dict):
                    apps_data = result.get("data", {})
                    if isinstance(apps_data, dict):
                        apps = apps_data.get("records", apps_data.get("apps", []))
                        total = apps_data.get("totalRecords", len(apps) if isinstance(apps, list) else 0)
                    else:
                        apps = apps_data if isinstance(apps_data, list) else []
                        total = len(apps) if isinstance(apps, list) else 0
                elif isinstance(result, list):
                    apps = result
                    total = len(apps)
                else:
                    self.logger.error(f"[InMobi] Unexpected response format: {type(result)}")
                    return []
                
                self.logger.info(f"[InMobi] Extracted {len(apps)} apps from API response (total: {total})")
                
                # Convert to standard format
                formatted_apps = []
                for app in apps:
                    if isinstance(app, dict):
                        # Extract app information (field names may vary)
                        app_id = app.get("appId") or app.get("id") or app.get("app_id")
                        app_name = app.get("appName") or app.get("name") or app.get("app_name")
                        platform = app.get("platform") or app.get("os") or "N/A"
                        status = app.get("status") or "N/A"
                        
                        formatted_apps.append({
                            "appCode": str(app_id) if app_id else "N/A",
                            "appId": str(app_id) if app_id else "N/A",  # For InMobi, appCode and appId are the same
                            "name": app_name or "Unknown",
                            "platform": platform,
                            "status": status,
                            "bundleId": app.get("bundleId") or app.get("bundle_id") or app.get("packageName") or "",  # For placement name generation
                        })
                
                self.logger.info(f"[InMobi] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                self.logger.error(f"[InMobi] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[InMobi] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return []