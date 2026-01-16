# utils/network_apis/bigoads_api.py
"""BigOAds API implementation"""
from typing import Dict, List, Optional
import requests
import json
import logging
import sys
import time
import hashlib
from api.base import BaseNetworkAPI
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)


class BigOAdsAPI(BaseNetworkAPI):
    """BigOAds API implementation"""
    
    def __init__(self):
        super().__init__("BigOAds")
        self.developer_id = get_env_var("BIGOADS_DEVELOPER_ID")
        self.token = get_env_var("BIGOADS_TOKEN")
    
    def _generate_signature(self, developer_id: str, token: str) -> tuple[str, str]:
        """Generate BigOAds API signature
        
        Args:
            developer_id: Developer ID from .env
            token: Token from .env
        
        Returns:
            Tuple of (signature_string, timestamp_milliseconds)
        """
        # Get current timestamp in milliseconds
        now = int(time.time() * 1000)
        
        # Step 1: Combine developerId-timestamp-token
        src = f"{developer_id}-{now}-{token}"
        
        # Step 2: Encrypt with SHA1
        encrypt = hashlib.sha1(src.encode('utf-8')).hexdigest()
        
        # Step 3: Connect encrypted string and timestamp with '.'
        sign = f"{encrypt}.{now}"
        
        return sign, str(now)
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get BigOAds API headers with signature"""
        if not self.developer_id or not self.token:
            return None
        
        sign, timestamp = self._generate_signature(self.developer_id, self.token)
        
        return {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": self.developer_id,
            "X-BIGO-Sign": sign
        }
    
    def create_app(self, payload: Dict) -> Dict:
        """Create app via BigOAds API"""
        url = "https://www.bigossp.com/open/app/add"
        
        if not self.developer_id or not self.token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to generate BigOAds signature"
            }
        
        # Remove None values from payload to avoid sending null
        cleaned_payload = {k: v for k, v in payload.items() if v is not None}
        
        self.logger.info(f"[BigOAds] API Request: POST {url}")
        self.logger.info(f"[BigOAds] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[BigOAds] Request Payload: {json.dumps(mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=cleaned_payload)
            response.raise_for_status()
            
            result = response.json()
            
            # BigOAds API 응답 형식에 맞게 정규화
            # BigOAds 응답 구조: {"code": "100", "msg": "...", "result": {"appCode": "...", ...}, "status": 0}
            if result.get("code") == "100" or result.get("code") == 0 or result.get("status") == 0:
                # result.result에 실제 데이터가 있음
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("result", result.get("data", result))
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or result.get("status") or "N/A"
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[BigOAds] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def create_unit(self, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit (slot) via BigOAds API"""
        url = "https://www.bigossp.com/open/slot/add"
        
        if not self.developer_id or not self.token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        headers = self._get_headers()
        if not headers:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to generate BigOAds signature"
            }
        
        # Print to stderr so it shows in console (Streamlit terminal)
        print("=" * 60, file=sys.stderr)
        print("[BigOAds] ========== CREATE UNIT REQUEST ==========", file=sys.stderr)
        print(f"[BigOAds] API Request: POST {url}", file=sys.stderr)
        
        # Log headers (mask sensitive data)
        masked_headers = mask_sensitive_data(headers.copy())
        print(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}", file=sys.stderr)
        
        # Log payload WITHOUT masking for debugging (no sensitive data in unit payload)
        print(f"[BigOAds] Request Payload (full): {json.dumps(payload, indent=2, ensure_ascii=False)}", file=sys.stderr)
        print(f"[BigOAds] Payload keys: {list(payload.keys())}", file=sys.stderr)
        print(f"[BigOAds] Payload values: {list(payload.values())}", file=sys.stderr)
        
        # Also log via logger
        self.logger.info(f"[BigOAds] ========== CREATE UNIT REQUEST ==========")
        self.logger.info(f"[BigOAds] API Request: POST {url}")
        self.logger.info(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}")
        self.logger.info(f"[BigOAds] Request Payload (full): {json.dumps(payload, indent=2, ensure_ascii=False)}")
        self.logger.info(f"[BigOAds] Payload keys: {list(payload.keys())}")
        self.logger.info(f"[BigOAds] Payload values: {list(payload.values())}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload, timeout=30)
            
            print(f"[BigOAds] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[BigOAds] Response Headers: {dict(response.headers)}", file=sys.stderr)
            
            # Try to parse JSON response
            try:
                result = response.json()
                print(f"[BigOAds] Response Body (JSON): {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            except ValueError:
                # If not JSON, log as text
                print(f"[BigOAds] Response Body (text): {response.text[:500]}", file=sys.stderr)
                result = {"status": 1, "code": "PARSE_ERROR", "msg": f"Non-JSON response: {response.text[:200]}"}
            
            # Also log via logger
            self.logger.info(f"[BigOAds] Response Status: {response.status_code}")
            self.logger.info(f"[BigOAds] Response Headers: {dict(response.headers)}")
            if "result" in locals():
                self.logger.info(f"[BigOAds] Response Body (JSON): {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # BigOAds API 응답 형식에 맞게 정규화
            if result.get("code") == 0 or result.get("status") == 0:
                print(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}", file=sys.stderr)
                self.logger.info(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("data", result)
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                error_code = result.get("code") or result.get("status") or "N/A"
                print(f"[BigOAds] ❌ Error: {error_code} - {error_msg}", file=sys.stderr)
                print(f"[BigOAds] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
                self.logger.error(f"[BigOAds] ❌ Error: {error_code} - {error_msg}")
                self.logger.error(f"[BigOAds] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            print(f"[BigOAds] ❌ API Error (Create Unit): {str(e)}", file=sys.stderr)
            print(f"[BigOAds] Error type: {type(e).__name__}", file=sys.stderr)
            
            if hasattr(e, 'response') and e.response is not None:
                print(f"[BigOAds] Response Status: {e.response.status_code}", file=sys.stderr)
                print(f"[BigOAds] Response Headers: {dict(e.response.headers)}", file=sys.stderr)
                try:
                    error_body = e.response.json()
                    print(f"[BigOAds] Error Response (JSON): {json.dumps(error_body, indent=2, ensure_ascii=False)}", file=sys.stderr)
                except:
                    error_text = e.response.text
                    print(f"[BigOAds] Error Response (text, first 500 chars): {error_text[:500]}", file=sys.stderr)
            else:
                print(f"[BigOAds] No response object available", file=sys.stderr)
            
            print("=" * 60, file=sys.stderr)
            
            # Also log via logger
            self.logger.error(f"[BigOAds] ❌ API Error (Create Unit): {str(e)}")
            self.logger.error(f"[BigOAds] Error type: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"[BigOAds] Response Status: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[BigOAds] Error Response (JSON): {json.dumps(error_body, indent=2, ensure_ascii=False)}")
                except:
                    self.logger.error(f"[BigOAds] Error Response (text): {e.response.text[:500]}")
            
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": f"Error creating unit: {str(e)}"
            }
    
    def get_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from BigOAds API"""
        # Add delay to avoid QPS limit (BigOAds has strict rate limiting)
        time.sleep(0.5)  # 500ms delay to avoid QPS limit
        
        url = "https://www.bigossp.com/open/app/list"
        
        if not self.developer_id or not self.token:
            self.logger.error("[BigOAds] BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set")
            return []
        
        headers = self._get_headers()
        if not headers:
            self.logger.error("[BigOAds] Failed to generate signature")
            return []
        
        # Request payload
        payload = {
            "pageNo": 1,
            "pageSize": 10
        }
        
        self.logger.info(f"[BigOAds] API Request: POST {url}")
        self.logger.info(f"[BigOAds] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        self.logger.info(f"[BigOAds] Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self._make_request("POST", url, headers=headers, json_data=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # BigOAds API 응답 형식에 맞게 처리
            # Response format: {"code": "100", "status": 0, "result": {"list": [...], "total": 12}}
            code = result.get("code")
            status = result.get("status")
            
            # Success: code == "100" or status == 0
            if code == "100" or status == 0:
                # Extract apps from result.list
                result_data = result.get("result", {})
                apps_list = result_data.get("list", [])
                
                self.logger.info(f"[BigOAds] Extracted {len(apps_list)} apps from API response (total: {result_data.get('total', 0)})")
                
                # Convert to standard format
                apps = []
                for app in apps_list:
                    platform_value = app.get("platform")
                    platform_str = "Android" if platform_value == 1 else ("iOS" if platform_value == 2 else "N/A")
                    
                    # BigOAds API response may have appId instead of appCode
                    app_code = app.get("appCode") or app.get("appId") or "N/A"
                    app_id = app.get("appId") or app.get("appCode")
                    
                    apps.append({
                        "appCode": app_code,
                        "appId": app_id,  # Store appId separately for reference
                        "name": app.get("name", "Unknown"),
                        "platform": platform_str,
                        "platformNum": platform_value,  # Keep original numeric value (1 or 2) for matching
                        "status": app.get("status", "N/A"),
                        "pkgName": app.get("pkgName", ""),  # Add pkgName for package name matching
                        "pkgNameDisplay": app.get("pkgNameDisplay", "")  # For BigOAds slot name generation
                    })
                
                self.logger.info(f"[BigOAds] Converted to {len(apps)} apps in standard format")
                return apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                self.logger.error(f"[BigOAds] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[BigOAds] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    self.logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    self.logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return []