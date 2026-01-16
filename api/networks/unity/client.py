"""Unity API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import base64
import urllib.parse
import sys
from api.base import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class UnityAPI(BaseNetworkAPI):
    """Unity API implementation"""
    
    def __init__(self):
        super().__init__("Unity")
        self.organization_id = get_env_var("UNITY_ORGANIZATION_ID")
        self.key_id = get_env_var("UNITY_KEY_ID")
        self.secret_key = get_env_var("UNITY_SECRET_KEY")
    
    def _get_headers(self, content_type: str = "application/json") -> Optional[Dict[str, str]]:
        """Get Unity API headers with Basic Authentication
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            Headers dictionary or None if credentials are missing
        """
        if not self.key_id or not self.secret_key:
            return None
        
        # Create Basic Auth header
        credentials = f"{self.key_id}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json"
        }
        
        if content_type:
            headers["Content-Type"] = content_type
        
        return headers
    
    def create_app(self, payload: Dict) -> Dict:
        """Create Unity project via Unity API
        
        API: POST https://services.api.unity.com/monetize/v1/organizations/{organizationId}/projects
        
        Authentication: Basic Authentication (KEY_ID:SECRET_KEY)
        
        Args:
            payload: Project creation payload
            
        Returns:
            API response dict
        """
        if not self.organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_ORGANIZATION_ID must be set in .env file or Streamlit secrets"
            }
        
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        url = f"https://services.api.unity.com/monetize/v1/organizations/{self.organization_id}/projects"
        headers = self._get_headers()
        
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        logger.info(f"[Unity] API Request: POST {url}")
        logger.info(f"[Unity] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Unity] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"[Unity] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Unity] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Unity] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Unity API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # Provide helpful error messages for common errors
                if response.status_code == 401:
                    logger.error("[Unity] 💡 인증 오류:")
                    logger.error("[Unity]   → UNITY_KEY_ID와 UNITY_SECRET_KEY를 확인해주세요.")
                elif response.status_code == 403:
                    logger.error("[Unity] 💡 권한 오류:")
                    logger.error("[Unity]   → API 접근 권한이 없습니다.")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] API Error (Create Project): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Unity] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Unity] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create Unity ad units (batch create)
        
        Note: Unity has a special structure. This method expects payload to contain:
        - project_id: Unity project ID (required)
        - store_name: Store name ("apple" or "google") (required)
        - ad_units: List of ad unit objects to create (required)
        
        Alternatively, payload can be a dict with these keys, or they can be passed separately.
        
        API: POST https://services.api.unity.com/monetize/v1/projects/{projectId}/stores/{storeName}/adunits
        
        Args:
            payload: Dict containing project_id, store_name, and ad_units list, 
                    OR just the ad_units list if project_id and store_name are in payload
            app_key: Not used for Unity (project_id is in payload)
            
        Returns:
            API response dict
        """
        # Extract project_id and store_name from payload
        project_id = payload.get("project_id") or payload.get("projectId")
        store_name = payload.get("store_name") or payload.get("storeName")
        ad_units = payload.get("ad_units") or payload.get("adUnits") or payload
        
        # If payload is a list, assume it's ad_units and use project_id/store_name from separate params
        if isinstance(payload, list):
            ad_units = payload
            # Try to get from app_key or other sources if needed
            if not project_id:
                # Fallback - would need to be passed differently
                return {
                    "status": 1,
                    "code": "INVALID_PAYLOAD",
                    "msg": "Unity create_unit requires project_id and store_name. Use create_ad_units method directly."
                }
        
        if not project_id or not store_name or not ad_units:
            return {
                "status": 1,
                "code": "INVALID_PAYLOAD",
                "msg": "Unity create_unit requires project_id, store_name, and ad_units list in payload"
            }
        
        return self.create_ad_units(project_id, store_name, ad_units)
    
    def create_ad_units(self, project_id: str, store_name: str, ad_units_payload: List[Dict]) -> Dict:
        """Create Unity ad units (batch create)
        
        API: POST https://services.api.unity.com/monetize/v1/projects/{projectId}/stores/{storeName}/adunits
        
        Args:
            project_id: Unity project ID
            store_name: Store name ("apple" or "google")
            ad_units_payload: List of ad unit objects to create
            
        Returns:
            API response dict
        """
        if not self.organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_ORGANIZATION_ID must be set in .env file or Streamlit secrets"
            }
        
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        headers = self._get_headers()
        
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        url = f"https://services.api.unity.com/monetize/v1/projects/{project_id}/stores/{store_name}/adunits"
        
        logger.info(f"[Unity] API Request: POST {url}")
        logger.info(f"[Unity] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Unity] Request Payload: {json.dumps(mask_sensitive_data(ad_units_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=ad_units_payload, headers=headers, timeout=30)
            
            logger.info(f"[Unity] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Unity] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Unity] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Unity API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result if result else {}
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # Provide helpful error messages for common errors
                if response.status_code == 401:
                    logger.error("[Unity] 💡 인증 오류:")
                    logger.error("[Unity]   → UNITY_KEY_ID와 UNITY_SECRET_KEY를 확인해주세요.")
                elif response.status_code == 403:
                    logger.error("[Unity] 💡 권한 오류:")
                    logger.error("[Unity]   → API 접근 권한이 없습니다.")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] API Error (Create Ad Units): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Unity] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Unity] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_placements(self, project_id: str, store_name: str, ad_unit_id: str, placements_payload: List[Dict]) -> Dict:
        """Create Unity placements (batch create)
        
        API: POST https://services.api.unity.com/monetize/v1/projects/{projectId}/stores/{storeName}/adunits/{adUnitId}/placements
        
        Args:
            project_id: Unity project ID
            store_name: Store name ("apple" or "google")
            ad_unit_id: Ad Unit ID (e.g., "iOS RV Bidding", "AOS IS Bidding")
            placements_payload: List of placement objects to create
            
        Returns:
            API response dict
        """
        if not self.organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_ORGANIZATION_ID must be set in .env file or Streamlit secrets"
            }
        
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        headers = self._get_headers()
        
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        # URL encode ad_unit_id (may contain spaces like "iOS RV Bidding")
        encoded_ad_unit_id = urllib.parse.quote(ad_unit_id, safe='')
        url = f"https://services.api.unity.com/monetize/v1/projects/{project_id}/stores/{store_name}/adunits/{encoded_ad_unit_id}/placements"
        
        logger.info(f"[Unity] API Request: POST {url}")
        logger.info(f"[Unity] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Unity] Request Payload: {json.dumps(mask_sensitive_data(placements_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=placements_payload, headers=headers, timeout=30)
            
            logger.info(f"[Unity] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Unity] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
                
                # Log detailed error information for 400 errors
                if response.status_code == 400 and isinstance(result, dict):
                    logger.error(f"[Unity] ========== 400 Validation Error Details ==========")
                    logger.error(f"[Unity] Full Response: {json.dumps(result, indent=2)}")
                    if "errors" in result:
                        logger.error(f"[Unity] Validation Errors: {json.dumps(result.get('errors'), indent=2)}")
                    # Check for other error fields
                    for key in ["error", "errorDetails", "validationErrors", "fieldErrors", "message"]:
                        if key in result:
                            logger.error(f"[Unity] {key}: {json.dumps(result.get(key), indent=2)}")
            except:
                logger.error(f"[Unity] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Unity API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result if result else {}
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # For 400 errors, include detailed error information
                if response.status_code == 400 and isinstance(result, dict):
                    if "errors" in result:
                        errors_detail = result.get("errors")
                        if errors_detail:
                            error_msg += f" - Errors: {json.dumps(errors_detail)}"
                    # Include all error-related fields in the response
                    error_response = {
                        "status": 1,
                        "code": error_code,
                        "msg": error_msg,
                        "errors": result.get("errors"),
                        "error": result.get("error"),
                        "errorDetails": result.get("errorDetails"),
                        "validationErrors": result.get("validationErrors"),
                        "fieldErrors": result.get("fieldErrors")
                    }
                    # Remove None values
                    error_response = {k: v for k, v in error_response.items() if v is not None}
                    return error_response
                
                # Provide helpful error messages for common errors
                if response.status_code == 401:
                    logger.error("[Unity] 💡 인증 오류:")
                    logger.error("[Unity]   → UNITY_KEY_ID와 UNITY_SECRET_KEY를 확인해주세요.")
                elif response.status_code == 403:
                    logger.error("[Unity] 💡 권한 오류:")
                    logger.error("[Unity]   → API 접근 권한이 없습니다.")
                elif response.status_code == 400:
                    logger.error("[Unity] 💡 요청 검증 오류:")
                    logger.error(f"[Unity]   → URL: {url}")
                    logger.error(f"[Unity]   → adUnitId (original): {ad_unit_id}")
                    logger.error(f"[Unity]   → adUnitId (encoded): {encoded_ad_unit_id}")
                    logger.error(f"[Unity]   → Payload: {json.dumps(mask_sensitive_data(placements_payload), indent=2)}")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] API Error (Create Placements): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Unity] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Unity] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def update_ad_units(self, project_id: str, store_name: str, ad_units_payload: Dict) -> Dict:
        """Update Unity ad units (archive existing ad units)
        
        API: PATCH https://services.api.unity.com/monetize/v1/projects/{projectId}/stores/{storeName}/adunits
        
        Args:
            project_id: Unity project ID
            store_name: Store name ("apple" or "google")
            ad_units_payload: Payload with ad units to update (archive=true)
            
        Returns:
            API response dict
        """
        if not self.organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_ORGANIZATION_ID must be set in .env file or Streamlit secrets"
            }
        
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        headers = self._get_headers()
        
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "UNITY_KEY_ID and UNITY_SECRET_KEY must be set in .env file or Streamlit secrets"
            }
        
        url = f"https://services.api.unity.com/monetize/v1/projects/{project_id}/stores/{store_name}/adunits"
        
        logger.info(f"[Unity] API Request: PATCH {url}")
        logger.info(f"[Unity] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Unity] Request Payload: {json.dumps(mask_sensitive_data(ad_units_payload), indent=2)}")
        
        try:
            response = requests.patch(url, json=ad_units_payload, headers=headers, timeout=30)
            
            logger.info(f"[Unity] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Unity] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Unity] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # Unity API 응답 형식에 맞게 정규화
            if response.status_code == 200 or response.status_code == 204:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result if result else {}
                }
            else:
                # Extract error message from response
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or response.status_code
                
                # Provide helpful error messages for common errors
                if response.status_code == 401:
                    logger.error("[Unity] 💡 인증 오류:")
                    logger.error("[Unity]   → UNITY_KEY_ID와 UNITY_SECRET_KEY를 확인해주세요.")
                elif response.status_code == 403:
                    logger.error("[Unity] 💡 권한 오류:")
                    logger.error("[Unity]   → API 접근 권한이 없습니다.")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] API Error (Update Ad Units): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Unity] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Unity] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get all projects (apps) from Unity API
        
        API: GET https://services.api.unity.com/monetize/v1/organizations/{organizationId}/projects
        
        Args:
            app_key: Not used for Unity (kept for interface compatibility)
            
        Returns:
            List of project dicts
        """
        if not self.organization_id:
            logger.error("[Unity] UNITY_ORGANIZATION_ID not found")
            return []
        
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return []
        
        headers = self._get_headers(content_type=None)
        
        if not headers:
            return []
        
        url = f"https://services.api.unity.com/monetize/v1/organizations/{self.organization_id}/projects"
        
        logger.info(f"[Unity] Fetching projects from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response - can be list or dict
                projects = []
                if isinstance(result, list):
                    projects = result
                elif isinstance(result, dict):
                    projects = result.get("data", result.get("projects", result.get("list", [])))
                    if not isinstance(projects, list):
                        projects = []
                
                # For Unity, ensure stores field is preserved (can be JSON string or dict)
                # The API might return stores as a JSON string that needs parsing
                for project in projects:
                    stores = project.get("stores", "")
                    if stores and isinstance(stores, str):
                        # Try to parse if it's a JSON string
                        try:
                            # Handle escaped JSON strings
                            parsed_stores = json.loads(stores)
                            # Keep both original string and parsed dict for compatibility
                            project["stores_parsed"] = parsed_stores
                        except (json.JSONDecodeError, TypeError):
                            # If parsing fails, keep original string
                            pass
                
                logger.info(f"[Unity] Retrieved {len(projects)} projects")
                if projects:
                    logger.info(f"[Unity] First project keys: {list(projects[0].keys())}")
                    logger.info(f"[Unity] First project stores type: {type(projects[0].get('stores', ''))}")
                
                return projects
            else:
                logger.error(f"[Unity] Failed to get projects: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Unity] Authentication failed - check KEY_ID and SECRET_KEY")
                elif response.status_code == 403:
                    logger.error("[Unity] Permission denied")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] Error fetching projects: {str(e)}")
            return []
    
    def get_ad_units(self, project_id: str) -> Dict:
        """Get ad units for a Unity project
        
        API: GET https://services.api.unity.com/monetize/v1/projects/{projectId}/adunits
        
        Args:
            project_id: Unity project ID
            
        Returns:
            Dict with "apple" and "google" keys containing ad units
        """
        if not self.key_id or not self.secret_key:
            logger.error("[Unity] UNITY_KEY_ID or UNITY_SECRET_KEY not found")
            return {}
        
        headers = self._get_headers(content_type=None)
        
        if not headers:
            return {}
        
        url = f"https://services.api.unity.com/monetize/v1/projects/{project_id}/adunits"
        
        logger.info(f"[Unity] Fetching ad units from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[Unity] Retrieved ad units for project {project_id}")
                logger.info(f"[Unity] Ad units response type: {type(result)}")
                if isinstance(result, dict):
                    logger.info(f"[Unity] Ad units response keys: {list(result.keys())}")
                    for key, value in result.items():
                        if isinstance(value, list):
                            logger.info(f"[Unity] {key} has {len(value)} units")
                            if value:
                                logger.info(f"[Unity] First {key} unit keys: {list(value[0].keys())}")
                                logger.info(f"[Unity] First {key} unit sample: {json.dumps(value[0], indent=2)[:500]}")
                        elif isinstance(value, dict):
                            logger.info(f"[Unity] {key} is dict with keys: {list(value.keys())}")
                return result  # Returns { "apple": {}, "google": {} }
            else:
                logger.error(f"[Unity] Failed to get ad units: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Unity] Authentication failed - check KEY_ID and SECRET_KEY")
                elif response.status_code == 403:
                    logger.error("[Unity] Permission denied")
                elif response.status_code == 404:
                    logger.error(f"[Unity] Project {project_id} not found")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"[Unity] Error fetching ad units: {str(e)}")
            return {}