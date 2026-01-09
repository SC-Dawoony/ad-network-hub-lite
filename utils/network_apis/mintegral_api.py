# utils/network_apis/mintegral_api.py
"""Mintegral API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import sys
import time
import hashlib
from .base_network_api import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class MintegralAPI(BaseNetworkAPI):
    """Mintegral API implementation"""
    
    def __init__(self):
        super().__init__("Mintegral")
        self.skey = get_env_var("MINTEGRAL_SKEY")
        self.secret = get_env_var("MINTEGRAL_SECRET")
    
    def _generate_signature(self, secret: str, timestamp: int) -> str:
        """Generate Mintegral API signature
        
        규칙: md5(SECRETmd5(time))
        
        Args:
            secret: Mintegral SECRET
            timestamp: Unix timestamp
            
        Returns:
            생성된 signature
        """
        # md5(time) 계산
        time_md5 = hashlib.md5(str(timestamp).encode()).hexdigest()
        
        # md5(SECRETmd5(time)) 계산
        sign_string = secret + time_md5
        signature = hashlib.md5(sign_string.encode()).hexdigest()
        
        return signature
    
    def _get_auth_params(self) -> Optional[Dict[str, str]]:
        """Get Mintegral API authentication parameters"""
        if not self.skey or not self.secret:
            return None
        
        current_time = int(time.time())
        signature = self._generate_signature(self.secret, current_time)
        
        return {
            "skey": self.skey,
            "time": str(current_time),
            "sign": signature
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via Mintegral API"""
        url = "https://dev.mintegral.com/app/open_api_create"
        
        if not self.skey or not self.secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        current_time = int(time.time())
        signature = self._generate_signature(self.secret, current_time)
        
        # Add authentication parameters to payload
        request_params = payload.copy()
        request_params["skey"] = self.skey
        request_params["time"] = str(current_time)
        request_params["sign"] = signature
        
        # Use form-urlencoded (matching Media List API pattern)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Print to console for debugging
        print("\n" + "=" * 80, file=sys.stderr)
        print("🟢 [Mintegral] ========== CREATE APP REQUEST ==========", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"[Mintegral] URL: {url}", file=sys.stderr)
        print(f"[Mintegral] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
        print(f"[Mintegral] Request Parameters (full): {json.dumps(request_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print(f"[Mintegral] Request Parameters Summary:", file=sys.stderr)
        for key, value in request_params.items():
            if key in ["sign", "skey"]:
                print(f"[Mintegral]   - {key}: {str(value)[:20]}... (masked)", file=sys.stderr)
            else:
                print(f"[Mintegral]   - {key}: {value} (type: {type(value).__name__})", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Also log via logger
        self.logger.info(f"[Mintegral] API Request: POST {url}")
        self.logger.info(f"[Mintegral] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Mintegral] Request Body: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # Use form-urlencoded
            response = self._make_request("POST", url, headers=headers, data=request_params, timeout=30)
            
            # Print to console for debugging
            print("\n" + "=" * 80, file=sys.stderr)
            print("🟢 [Mintegral] ========== CREATE APP RESPONSE ==========", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(f"[Mintegral] Response Status: {response.status_code}", file=sys.stderr)
            
            result = response.json()
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            
            # Also log via logger
            self.logger.info(f"[Mintegral] Response Status: {response.status_code}")
            self.logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format:
            # Success: {"code": 0, "msg": "Success", ...}
            # Error: {"code": -2007, "msg": "Invalid Params", "traceid": "..."}
            top_level_code = result.get("code")
            
            # Success: code must be 0 or 200 (positive or zero)
            # Error: code is negative (e.g., -2007, -2004)
            if top_level_code is not None:
                if top_level_code == 0 or top_level_code == 200:
                    # Success
                    print(f"[Mintegral] ✅ Success (code: {top_level_code})", file=sys.stderr)
                    self.logger.info(f"[Mintegral] ✅ Success (code: {top_level_code})")
                    return {
                        "status": 0,
                        "code": 0,
                        "msg": result.get("msg", "Success"),
                        "result": result.get("result", result.get("data", result))
                    }
                else:
                    # Error: negative code or non-zero positive code
                    error_msg = result.get("msg") or "Unknown error"
                    print(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}", file=sys.stderr)
                    self.logger.error(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}")
                    return {
                        "status": 1,
                        "code": top_level_code,
                        "msg": error_msg
                    }
            
            # Fallback: if code is not present, check HTTP status
            if response.status_code == 200:
                print(f"[Mintegral] ✅ Success (HTTP 200, no code in response)", file=sys.stderr)
                self.logger.info(f"[Mintegral] ✅ Success (HTTP 200, no code in response)")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("result", result.get("data", result))
                }
            else:
                error_msg = result.get("msg") or "Unknown error"
                print(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}", file=sys.stderr)
                self.logger.error(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}")
                return {
                    "status": 1,
                    "code": response.status_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Mintegral] API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create ad placement (unit) via Mintegral API"""
        url = "https://dev.mintegral.com/v2/placement/open_api_create"
        
        if not self.skey or not self.secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        current_time = int(time.time())
        signature = self._generate_signature(self.secret, current_time)
        
        # Add authentication fields to payload
        api_payload = payload.copy()
        api_payload["skey"] = self.skey
        api_payload["time"] = str(current_time)
        api_payload["sign"] = signature
        
        # Use form-urlencoded
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        self.logger.info(f"[Mintegral] API Request: POST {url}")
        self.logger.info(f"[Mintegral] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[Mintegral] Request Body: {json.dumps(mask_sensitive_data(api_payload), indent=2)}")
        
        try:
            # Use data= instead of json= for form-urlencoded
            response = self._make_request("POST", url, headers=headers, data=api_payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            self.logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format normalization
            top_level_code = result.get("code")
            
            if top_level_code is not None:
                if top_level_code == 0 or top_level_code == 200:
                    # Success
                    self.logger.info(f"[Mintegral] ✅ Success (code: {top_level_code})")
                    result_data = result.get("data")
                    if result_data is None:
                        result_data = result.get("result", {})
                    
                    msg = result.get("msg", "Success")
                    if not result_data and "empty response" in msg.lower():
                        result_data = {}
                    
                    return {
                        "status": 0,
                        "code": 0,
                        "msg": msg,
                        "result": result_data if result_data else {}
                    }
                else:
                    # Error
                    error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                    self.logger.error(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}")
                    return {
                        "status": 1,
                        "code": top_level_code,
                        "msg": error_msg
                    }
            
            # Fallback: if code is not present, check status field
            if result.get("status") == 0:
                result_data = result.get("data") or result.get("result", {})
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result_data if result_data else {}
                }
            else:
                error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                error_code = result.get("code") or result.get("ret_code") or result.get("status") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[Mintegral] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get media list from Mintegral API"""
        url = "https://dev.mintegral.com/v2/app/open_api_list"
        
        if not self.skey or not self.secret:
            self.logger.error("[Mintegral] MINTEGRAL_SKEY or MINTEGRAL_SECRET not found")
            return []
        
        # Generate timestamp and signature
        current_time = int(time.time())
        signature = self._generate_signature(self.secret, current_time)
        
        # Build request params (GET request with query parameters)
        request_params = {
            "skey": self.skey,
            "time": str(current_time),
            "sign": signature
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Print to console for debugging
        print("\n" + "=" * 80, file=sys.stderr)
        print("🟢 [Mintegral] ========== GET MEDIA LIST REQUEST ==========", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"[Mintegral] URL: {url}", file=sys.stderr)
        print(f"[Mintegral] Headers: {json.dumps(headers, indent=2)}", file=sys.stderr)
        print(f"[Mintegral] Request Params: {json.dumps(request_params, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Also log via logger
        self.logger.info(f"[Mintegral] API Request: GET {url}")
        self.logger.info(f"[Mintegral] Request Headers: {json.dumps(headers, indent=2)}")
        self.logger.info(f"[Mintegral] Request Params: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # GET request with params
            response = self._make_request("GET", url, headers=headers, params=request_params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Print to console
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            self.logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Check response code
            response_code = result.get("code")
            response_msg = result.get("msg")
            data = result.get("data")
            
            print(f"[Mintegral] Response code: {response_code}", file=sys.stderr)
            print(f"[Mintegral] Response msg: {response_msg}", file=sys.stderr)
            
            if response_code != 200:
                error_msg = response_msg or "Unknown error"
                print(f"[Mintegral] ❌ Error: code={response_code}, msg={error_msg}", file=sys.stderr)
                self.logger.error(f"[Mintegral] Error: code={response_code}, msg={error_msg}")
                
                # Common error codes
                error_codes = {
                    -2004: "No Access - 인증 실패 (skey, secret, sign 확인)",
                    -2006: "Permission denied - 권한 없음",
                    -2007: "Invalid Params - 잘못된 파라미터"
                }
                if response_code in error_codes:
                    print(f"[Mintegral] 💡 {error_codes[response_code]}", file=sys.stderr)
                
                return []
            
            # Parse response
            if isinstance(data, dict):
                lists = data.get("lists", [])
                total = data.get("total", 0)
                page = data.get("page", 1)
                per_page = data.get("per_page", 0)
                
                print(f"[Mintegral] Response data structure:", file=sys.stderr)
                print(f"[Mintegral]   - total: {total}", file=sys.stderr)
                print(f"[Mintegral]   - page: {page}", file=sys.stderr)
                print(f"[Mintegral]   - per_page: {per_page}", file=sys.stderr)
                print(f"[Mintegral]   - lists length: {len(lists) if isinstance(lists, list) else 0}", file=sys.stderr)
                
                apps_data = lists if isinstance(lists, list) else []
            else:
                apps_data = []
            
            # Format apps to standard format
            formatted_apps = []
            for app in apps_data:
                if isinstance(app, dict):
                    formatted_apps.append({
                        "appCode": str(app.get("app_id", app.get("id", app.get("media_id", "N/A")))),
                        "app_id": app.get("app_id", app.get("id", app.get("media_id"))),
                        "name": app.get("app_name", app.get("name", app.get("media_name", "Unknown"))),
                        "platform": app.get("os", app.get("platform", "N/A")),
                        "pkgName": app.get("package", app.get("pkg_name", app.get("package_name", ""))),
                    })
            
            print(f"[Mintegral] ✅ Successfully loaded {len(formatted_apps)} apps from API", file=sys.stderr)
            self.logger.info(f"[Mintegral] Successfully loaded {len(formatted_apps)} apps from API")
            
            return formatted_apps
            
        except requests.exceptions.RequestException as e:
            print(f"[Mintegral] ❌ API Error (Get Apps): {str(e)}", file=sys.stderr)
            self.logger.error(f"[Mintegral] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    print(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2, ensure_ascii=False)}", file=sys.stderr)
                    self.logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    print(f"[Mintegral] Error Response (text): {e.response.text[:500]}", file=sys.stderr)
                    self.logger.error(f"[Mintegral] Error Response (text): {e.response.text[:500]}")
            return []
        except Exception as e:
            print(f"[Mintegral] ❌ Unexpected Error (Get Apps): {str(e)}", file=sys.stderr)
            self.logger.error(f"[Mintegral] Unexpected Error (Get Apps): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []