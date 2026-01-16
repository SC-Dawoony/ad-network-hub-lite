"""Pangle (TikTok) API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import sys
import time
import random
import hashlib
import re
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class PangleAPI(BaseNetworkAPI):
    """Pangle (TikTok) API implementation"""
    
    def __init__(self):
        super().__init__("Pangle")
        self.security_key = get_env_var("PANGLE_SECURITY_KEY")
        self.user_id = get_env_var("PANGLE_USER_ID")
        self.role_id = get_env_var("PANGLE_ROLE_ID")
        # Check if sandbox mode is enabled
        sandbox_env = get_env_var("PANGLE_SANDBOX")
        self.sandbox = sandbox_env and sandbox_env.lower() == "true" if sandbox_env else False
        
        # API endpoints
        if self.sandbox:
            self.base_url = "http://open-api-sandbox.pangleglobal.com"
        else:
            self.base_url = "https://open-api.pangleglobal.com"
    
    def _generate_signature(self, security_key: str, timestamp: int, nonce: int) -> str:
        """Generate Pangle API signature
        
        Signature generation (exact implementation as per Pangle documentation):
        
        import hashlib
        keys = [security_key, str(timestamp), str(nonce)] 
        keys.sort() 
        keyStr = ''.join(keys) 
        signature = hashlib.sha1(keyStr.encode("utf-8")).hexdigest()
        
        Args:
            security_key: Pangle security key
            timestamp: Unix timestamp (seconds)
            nonce: Random integer (1 to 2^31-1)
            
        Returns:
            Lowercase hex digest (40 characters)
        """
        # Exact implementation as per Pangle documentation
        keys = [security_key, str(timestamp), str(nonce)]
        keys.sort()
        keyStr = ''.join(keys)
        signature = hashlib.sha1(keyStr.encode("utf-8")).hexdigest()
        
        logger.info(f"[Pangle] Signature generation:")
        logger.info(f"[Pangle]   security_key: {security_key[:20]}... (length: {len(security_key)})")
        logger.info(f"[Pangle]   timestamp: {timestamp}")
        logger.info(f"[Pangle]   nonce: {nonce}")
        logger.info(f"[Pangle]   keys (before sort): [{security_key[:20]}..., '{timestamp}', '{nonce}']")
        logger.info(f"[Pangle]   keys (after sort): {keys}")
        logger.info(f"[Pangle]   keyStr: {keyStr[:50]}... (length: {len(keyStr)})")
        logger.info(f"[Pangle]   signature: {signature} (length: {len(signature)})")
        
        return signature
    
    def _build_auth_params(self, payload: Optional[Dict] = None) -> Optional[Dict]:
        """Build authentication parameters (timestamp, nonce, sign)
        
        Args:
            payload: Optional payload that may contain user_id and role_id
            
        Returns:
            Dict with user_id, role_id, timestamp, nonce, sign, version, or None if error
        """
        if not self.security_key:
            logger.error("[Pangle] PANGLE_SECURITY_KEY not found in environment")
            return None
        
        # Get user_id and role_id from environment variables only
        # Always use .env values to ensure consistency
        user_id = self.user_id
        role_id = self.role_id
        
        if not user_id or not role_id:
            logger.error("[Pangle] PANGLE_USER_ID and PANGLE_ROLE_ID must be set")
            return None
        
        try:
            user_id_int = int(user_id)
            role_id_int = int(role_id)
        except (ValueError, TypeError):
            logger.error("[Pangle] PANGLE_USER_ID and PANGLE_ROLE_ID must be integers")
            return None
        
        # Generate timestamp and nonce immediately before API call
        # to ensure they are fresh and signature matches
        timestamp = int(time.time())
        nonce = random.randint(1, 2147483647)
        version = "1.0"
        
        # Generate signature
        sign = self._generate_signature(self.security_key, timestamp, nonce)
        
        # Check timestamp freshness
        current_time_check = int(time.time())
        timestamp_age = current_time_check - timestamp
        if timestamp_age > 1:
            logger.warning(f"[Pangle] WARNING: Timestamp is {timestamp_age} seconds old! This may cause validation failure.")
        
        return {
            "user_id": user_id_int,
            "role_id": role_id_int,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": sign,
            "version": version,
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via Pangle API
        
        Note: payload from build_app_payload() contains only user-input fields.
        This method adds authentication fields: timestamp, nonce, sign, version, status.
        
        Args:
            payload: App creation payload
            
        Returns:
            API response dict
        """
        if not self.security_key:
            logger.error("[Pangle] PANGLE_SECURITY_KEY not found in environment")
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_SECURITY_KEY must be set in .env file or Streamlit secrets"
            }
        
        logger.info(f"[Pangle] Starting app creation with payload keys: {list(payload.keys())}")
        logger.info(f"[Pangle] PANGLE_SANDBOX: {'enabled' if self.sandbox else 'disabled (Production)'}")
        
        # Build auth params
        auth_params = self._build_auth_params(payload)
        if not auth_params:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be set in .env file or provided in form"
            }
        
        # Set status based on environment
        status = 6 if self.sandbox else 2  # 6 = test, 2 = Live
        
        # Build request parameters
        # Start with auth_params (user_id, role_id, timestamp, nonce, sign)
        request_params = auth_params.copy()
        
        # Add status
        request_params["status"] = status
        
        # Add all fields from payload (most of the request body)
        # This includes: app_name, download_url, app_category_code, version, mask_rule_ids, coppa_value
        request_params.update(payload)
        
        # Build URL
        url = f"{self.base_url}/union/media/open_api/site/create"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Log request with detailed signature information
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Security Key: {'SET' if self.security_key else 'NOT SET'} (length: {len(self.security_key) if self.security_key else 0})")
        logger.info(f"[Pangle] User ID: {request_params['user_id']}, Role ID: {request_params['role_id']}")
        logger.info(f"[Pangle] Timestamp: {request_params['timestamp']}, Nonce: {request_params['nonce']}")
        logger.info(f"[Pangle] Signature: {request_params['sign']} (length: {len(request_params['sign'])})")
        
        # Log signature generation details
        keys_for_signature = [self.security_key, str(request_params['timestamp']), str(request_params['nonce'])]
        keys_for_signature.sort()
        key_str_for_signature = ''.join(keys_for_signature)
        logger.info(f"[Pangle] Signature generation details:")
        logger.info(f"[Pangle]   - Security Key: {self.security_key[:10]}... (length: {len(self.security_key)})")
        logger.info(f"[Pangle]   - Timestamp: {request_params['timestamp']}")
        logger.info(f"[Pangle]   - Nonce: {request_params['nonce']}")
        logger.info(f"[Pangle]   - Sorted keys: {keys_for_signature}")
        logger.info(f"[Pangle]   - Concatenated string: {key_str_for_signature}")
        logger.info(f"[Pangle]   - Generated signature: {request_params['sign']}")
        logger.info(f"[Pangle]   - Signature length: {len(request_params['sign'])} (expected: 40)")
        
        # Verify signature is lowercase
        if request_params['sign'] != request_params['sign'].lower():
            logger.warning(f"[Pangle] WARNING: Signature contains uppercase characters!")
        
        masked_params = mask_sensitive_data(request_params.copy())
        if "sign" in masked_params:
            masked_params["sign"] = "***MASKED***"
        logger.info(f"[Pangle] Full Request Params (masked): {json.dumps(masked_params, indent=2)}")
        
        # Log request structure check
        logger.info(f"[Pangle] Request structure check:")
        logger.info(f"[Pangle]   - Has user_id: {('user_id' in request_params)}")
        logger.info(f"[Pangle]   - Has role_id: {('role_id' in request_params)}")
        logger.info(f"[Pangle]   - Has timestamp: {('timestamp' in request_params)}")
        logger.info(f"[Pangle]   - Has nonce: {('nonce' in request_params)}")
        logger.info(f"[Pangle]   - Has sign: {('sign' in request_params)}")
        logger.info(f"[Pangle]   - Has version: {('version' in request_params)}")
        logger.info(f"[Pangle]   - Version value: {request_params.get('version')}")
        logger.info(f"[Pangle]   - Has status: {('status' in request_params)}")
        logger.info(f"[Pangle]   - Status value: {request_params.get('status')}")
        
        try:
            # Verify timestamp is still fresh (re-check right before API call)
            current_time_before_request = int(time.time())
            timestamp_age_seconds = current_time_before_request - request_params['timestamp']
            logger.info(f"[Pangle] Timestamp age before request: {timestamp_age_seconds} seconds")
            
            if timestamp_age_seconds > 5:
                logger.warning(f"[Pangle] WARNING: Timestamp is {timestamp_age_seconds} seconds old! Regenerating...")
                # Regenerate timestamp and nonce if too old
                timestamp = int(time.time())
                nonce = random.randint(1, 2147483647)
                sign = self._generate_signature(self.security_key, timestamp, nonce)
                # Update request_params with fresh values
                request_params["timestamp"] = timestamp
                request_params["nonce"] = nonce
                request_params["sign"] = sign
                logger.info(f"[Pangle] Regenerated: timestamp={timestamp}, nonce={nonce}, sign={sign[:20]}...")
            
            # Log actual JSON being sent
            print("=" * 60, file=sys.stderr)
            print("[Pangle] ========== CREATE APP REQUEST ==========", file=sys.stderr)
            print(f"[Pangle] URL: {url}", file=sys.stderr)
            print(f"[Pangle] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
            print(f"[Pangle] Request Body (full):", file=sys.stderr)
            # Create a copy for logging (mask sensitive data)
            log_params = request_params.copy()
            if "sign" in log_params:
                log_params["sign"] = f"{log_params['sign'][:20]}... (masked, full length: {len(log_params['sign'])})"
            print(f"[Pangle] {json.dumps(log_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Pangle] ========== FINAL REQUEST BEING SENT ==========")
            logger.info(f"[Pangle] URL: {url}")
            logger.info(f"[Pangle] Headers: {json.dumps(headers, indent=2)}")
            logger.info(f"[Pangle] Request Body (full):")
            logger.info(f"[Pangle] {json.dumps(log_params, indent=2, ensure_ascii=False)}")
            logger.info(f"[Pangle] ===============================================")
            
            response = requests.post(url, json=request_params, headers=headers, timeout=30)
            
            # Log response status
            print(f"[Pangle] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[Pangle] Response Headers: {dict(response.headers)}", file=sys.stderr)
            
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            logger.info(f"[Pangle] Response Headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Log response
            print(f"[Pangle] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            logger.info(f"[Pangle] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Parse error response if needed
            error_code = result.get("code") or result.get("ret_code")
            error_msg = result.get("msg") or result.get("message") or "Unknown error"
            
            if error_code != 0 and error_code is not None:
                print(f"[Pangle] ❌ Error: {error_code} - {error_msg}", file=sys.stderr)
                print(f"[Pangle] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
                
                # Parse 50003 error to extract internal_code and internal_message
                if error_code == 50003:
                    self._parse_error_response(error_msg, request_params, url)
            
            # Normalize response
            if result.get("code") == 0 or result.get("ret_code") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result.get("data", result)
                }
            else:
                # Extract internal_code from 50003 error messages for better error reporting
                if error_code == 50003:
                    internal_code_match = re.search(r'Internal code:\[(\d+)\]', str(error_msg))
                    if internal_code_match:
                        internal_code = internal_code_match.group(1)
                        error_msg = f"{error_msg} (Internal Code: {internal_code})"
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create ad placement (unit) via Pangle API
        
        Args:
            payload: Unit creation payload
            app_key: Not used for Pangle (app_id is in payload)
            
        Returns:
            API response dict
        """
        if not self.security_key:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_SECURITY_KEY must be set in .env file or Streamlit secrets"
            }
        
        # Build auth params
        auth_params = self._build_auth_params()
        if not auth_params:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "PANGLE_USER_ID and PANGLE_ROLE_ID must be set in .env file"
            }
        
        # Build request parameters
        request_params = auth_params.copy()
        
        # Add payload fields to request_params
        # Note: ad_placement_type in payload should be ad_slot_type in API
        api_payload = payload.copy()
        if "ad_placement_type" in api_payload:
            api_payload["ad_slot_type"] = api_payload.pop("ad_placement_type")
        
        request_params.update(api_payload)
        
        # Build URL
        url = f"{self.base_url}/union/media/open_api/code/create"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Pangle] Request Params: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers, timeout=30)
            
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Pangle] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Normalize response
            if result.get("code") == 0 or result.get("ret_code") == 0:
                return {
                    "status": 0,
                    "code": 0,
                    "msg": "Success",
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                error_code = result.get("code") or result.get("ret_code") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _parse_error_response(self, error_msg: str, request_params: Dict, url: str) -> None:
        """Parse and log detailed error response information
        
        Args:
            error_msg: Error message from API
            request_params: Request parameters used
            url: Request URL
        """
        # Parse "Internal code:[50001], internal message:[API System error]"
        internal_code_match = re.search(r'Internal code:\[(\d+)\]', str(error_msg))
        internal_msg_match = re.search(r'internal message:\[([^\]]+)\]', str(error_msg))
        
        if internal_code_match:
            internal_code = internal_code_match.group(1)
            internal_message = internal_msg_match.group(1) if internal_msg_match else "Unknown internal error"
            
            print(f"[Pangle] ⚠️  Internal Error Details:", file=sys.stderr)
            print(f"[Pangle]   - Internal Code: {internal_code}", file=sys.stderr)
            print(f"[Pangle]   - Internal Message: {internal_message}", file=sys.stderr)
            print(f"[Pangle]   - Note: 50003 indicates an error occurred when API server calls its subordinate HTTP services", file=sys.stderr)
            print(f"[Pangle]   - Refer to section 5.1.3 Internal Code List for details about code {internal_code}", file=sys.stderr)
            
            logger.error(f"[Pangle] Internal Error Details:")
            logger.error(f"[Pangle]   - Internal Code: {internal_code}")
            logger.error(f"[Pangle]   - Internal Message: {internal_message}")
            
            # Handle specific internal codes
            internal_code_descriptions = {
                "0": "Success - Operation successful",
                "SY_1000": "System error - Unknown system error",
                "SY_1001": "Parameter error - Failed to parse the request",
                "SY_1009": "Database error - An error has occurred in the database",
                "SY_1005": "Permission denied - Insufficient permissions",
                "SY_1011": "Invalid value for the field - The value of the field does not meet the requirements",
                "SY_1012": "The field cannot be modified - Due to some restrictions, the target field cannot be edited",
                "SY_1013": "Missing required field - Some essential fields are missing",
                "21000": "Download URL error - The app download URL is incorrect",
                "21001": "App downloading error - Failed to download the app",
                "21003": "Package parsing error - Failed to parse the app package",
                "21005": "Verification failed - The download link format is not correct",
                "21007": "Application package name is blocked - Verification failed",
                "21008": "Unsupported app store - This app store is not supported yet",
                "21011": "Package name error - Package name is incorrect",
                "21012": "SHA1 error - SHA1 is incorrect",
                "21014": "App validation still in processing - Verification has timed out",
                "21017": "Package name already exist - This package name already exists",
                "21020": "App downloading time out - App download has timed out",
                "21023": "App store has not been registered by media - This app store is not supported",
            }
            
            if internal_code in internal_code_descriptions:
                description = internal_code_descriptions[internal_code]
                print(f"[Pangle]   - Internal Code {internal_code}: {description}", file=sys.stderr)
                logger.error(f"[Pangle]   - Internal Code {internal_code}: {description}")
            elif internal_code == "50001":
                print(f"[Pangle]   - Internal Code 50001: System error (Return Code)", file=sys.stderr)
                logger.error(f"[Pangle]   - Internal Code 50001: System error (Return Code)")
            elif internal_code == "41001":
                print(f"[Pangle]   - Internal Code 41001: OAuth validation failure", file=sys.stderr)
                logger.error(f"[Pangle]   - Internal Code 41001: OAuth validation failure")
                logger.error(f"[Pangle]   - Security Key length: {len(self.security_key) if self.security_key else 0}")
                logger.error(f"[Pangle]   - User ID: {request_params.get('user_id')}, Role ID: {request_params.get('role_id')}")
                logger.error(f"[Pangle]   - Timestamp: {request_params.get('timestamp')}, Nonce: {request_params.get('nonce')}")
                logger.error(f"[Pangle]   - Signature: {request_params.get('sign')}")
                logger.error(f"[Pangle]   - Request URL: {url}")
            
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from Pangle API
        
        API: POST /union/media/open_api/site/query
        
        Args:
            app_key: Optional app ID to filter by (will be used as app_id filter)
            
        Returns:
            List of app dicts with standard format:
            - appCode/appId: app_id
            - name: app_name
            - platform: os_type
            - status: status
            - packageName: package_name
            - etc.
        """
        if not self.security_key:
            logger.error("[Pangle] PANGLE_SECURITY_KEY not found in environment")
            return []
        
        # Build auth params
        auth_params = self._build_auth_params()
        if not auth_params:
            logger.error("[Pangle] Failed to build auth params for get_apps")
            return []
        
        # Build request parameters
        request_params = auth_params.copy()
        request_params.update({
            "page": 1,
            "page_size": 500,  # Max page size
        })
        
        # Add app_id filter if app_key is provided
        if app_key:
            try:
                app_id_int = int(app_key)
                request_params["app_id"] = [app_id_int]
            except (ValueError, TypeError):
                logger.warning(f"[Pangle] Invalid app_key format: {app_key}, ignoring filter")
        
        # Build URL
        url = f"{self.base_url}/union/media/open_api/site/query"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Request Params: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers, timeout=30)
            
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Pangle] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Check response code
            error_code = result.get("code") or result.get("ret_code")
            if error_code != 0 and error_code is not None:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                logger.error(f"[Pangle] API Error (Get Apps): {error_code} - {error_msg}")
                return []
            
            # Extract app_list from response
            data = result.get("data", {})
            app_list = data.get("app_list", [])
            
            logger.info(f"[Pangle] Retrieved {len(app_list)} apps")
            
            # Convert to standard format
            apps = []
            for app in app_list:
                # Map Pangle API response to standard format
                apps.append({
                    "appCode": str(app.get("app_id", "")),
                    "appId": app.get("app_id"),
                    "name": app.get("app_name", ""),
                    "platform": "Android" if app.get("os_type") == "android" else ("iOS" if app.get("os_type") == "ios" else app.get("os_type", "")),
                    "status": app.get("status"),
                    "packageName": app.get("package_name", ""),
                    "downloadUrl": app.get("download_url", ""),
                    "categoryCode": app.get("app_category_code"),
                    "userId": app.get("user_id"),
                    "maskRuleIds": app.get("mask_rule_ids", []),
                    "coppaValue": app.get("coppa_value"),
                    "downloadAddress": app.get("download_address"),
                })
            
            return apps
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return []
    
    def get_units(self, app_code: str) -> List[Dict]:
        """Get ad placements (units) list for an app from Pangle API
        
        API: POST /union/media/open_api/code/query
        
        Args:
            app_code: App ID (site_id) to filter by
            
        Returns:
            List of ad unit dicts with standard format:
            - slotCode/adSlotId: ad_slot_id
            - name: ad_slot_name
            - adType: ad_slot_type
            - status: status
            - appId: app_id
            - etc.
        """
        if not self.security_key:
            logger.error("[Pangle] PANGLE_SECURITY_KEY not found in environment")
            return []
        
        # Build auth params
        auth_params = self._build_auth_params()
        if not auth_params:
            logger.error("[Pangle] Failed to build auth params for get_units")
            return []
        
        # Build request parameters
        request_params = auth_params.copy()
        request_params.update({
            "page": 1,
            "page_size": 500,  # Max page size
        })
        
        # Add app_id filter if app_code is provided
        if app_code:
            try:
                app_id_int = int(app_code)
                request_params["app_id"] = [app_id_int]
            except (ValueError, TypeError):
                logger.warning(f"[Pangle] Invalid app_code format: {app_code}, ignoring filter")
        
        # Build URL
        url = f"{self.base_url}/union/media/open_api/code/query"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"[Pangle] API Request: POST {url}")
        logger.info(f"[Pangle] Request Params: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            response = requests.post(url, json=request_params, headers=headers, timeout=30)
            
            logger.info(f"[Pangle] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Pangle] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Check response code
            error_code = result.get("code") or result.get("ret_code")
            if error_code != 0 and error_code is not None:
                error_msg = result.get("message") or result.get("msg") or "Unknown error"
                logger.error(f"[Pangle] API Error (Get Units): {error_code} - {error_msg}")
                return []
            
            # Extract ad_slot_list from response
            data = result.get("data", {})
            ad_slot_list = data.get("ad_slot_list", [])
            
            logger.info(f"[Pangle] Retrieved {len(ad_slot_list)} ad units")
            
            # Convert to standard format
            units = []
            for slot in ad_slot_list:
                # Map Pangle API response to standard format
                units.append({
                    "slotCode": str(slot.get("ad_slot_id", "")),
                    "adSlotId": slot.get("ad_slot_id"),
                    "name": slot.get("ad_slot_name", ""),
                    "adType": slot.get("ad_slot_type"),
                    "status": slot.get("status"),
                    "appId": slot.get("app_id"),
                    "appName": slot.get("app_name", ""),
                    "renderType": slot.get("render_type"),
                    "maskRuleId": slot.get("mask_rule_id"),
                    "maskRuleIds": slot.get("mask_rule_ids", []),
                    "biddingType": slot.get("bidding_type"),
                    "adCategories": slot.get("ad_categories", []),
                    "width": slot.get("width"),
                    "height": slot.get("height"),
                    "orientation": slot.get("orientation"),
                    "rewardName": slot.get("reward_name"),
                    "rewardCount": slot.get("reward_count"),
                    "rewardIsCallback": slot.get("reward_is_callback"),
                    "rewardCallbackUrl": slot.get("reward_callback_url"),
                    "rewardSecurityKey": slot.get("reward_security_key"),
                    "cpm": slot.get("cpm"),
                    "useMediation": slot.get("use_mediation"),
                    "acceptMaterialType": slot.get("accept_material_type"),
                })
            
            return units
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pangle] API Error (Get Units): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Pangle] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Pangle] Error Response (text): {e.response.text}")
            return []