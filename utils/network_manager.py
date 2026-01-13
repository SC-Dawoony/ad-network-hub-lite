"""Network Manager - Centralized API client management"""
import logging
import json
import requests
import base64
import time
import hashlib
from typing import Dict, List, Optional, Any
from utils.helpers import get_env_var, mask_sensitive_data

logger = logging.getLogger(__name__)

# Note: This is a placeholder for the actual AdNetworkManager
# In a real implementation, this would import from BE/services/ad_network_manager.py
# For now, we'll create a mock implementation for demonstration


class MockNetworkManager:
    """Mock network manager for demonstration purposes"""
    
    def __init__(self):
        self.clients = {}
        # Initialize network API instances
        self._ironsource_api = None
        self._bigoads_api = None
        self._mintegral_api = None
        self._inmobi_api = None
        self._fyber_api = None
        self._applovin_api = None
        self._unity_api = None
        self._pangle_api = None
    
    def get_client(self, network: str):
        """Get API client for a network"""
        return self.clients.get(network)
    
    def create_app(self, network: str, payload: Dict) -> Dict:
        """Create app via network API"""
        if network == "ironsource":
            return self._create_ironsource_app(payload)
        elif network == "pangle":
            # Use new PangleAPI
            if self._pangle_api is None:
                from utils.network_apis.pangle_api import PangleAPI
                self._pangle_api = PangleAPI()
            return self._pangle_api.create_app(payload)
        elif network == "bigoads":
            # Use new BigOAdsAPI
            if self._bigoads_api is None:
                from utils.network_apis.bigoads_api import BigOAdsAPI
                self._bigoads_api = BigOAdsAPI()
            return self._bigoads_api.create_app(payload)
        elif network == "mintegral":
            # Use new MintegralAPI
            if self._mintegral_api is None:
                from utils.network_apis.mintegral_api import MintegralAPI
                self._mintegral_api = MintegralAPI()
            return self._mintegral_api.create_app(payload)
        elif network == "inmobi":
            # Use new InMobiAPI
            if self._inmobi_api is None:
                from utils.network_apis.inmobi_api import InMobiAPI
                self._inmobi_api = InMobiAPI()
            return self._inmobi_api.create_app(payload)
        elif network == "fyber":
            # Use new FyberAPI
            if self._fyber_api is None:
                from utils.network_apis.fyber_api import FyberAPI
                self._fyber_api = FyberAPI()
            return self._fyber_api.create_app(payload)
        elif network == "unity":
            # Use new UnityAPI
            if self._unity_api is None:
                from utils.network_apis.unity_api import UnityAPI
                self._unity_api = UnityAPI()
            return self._unity_api.create_app(payload)
        
        # Mock implementation for other networks
        logger.info(f"[{network.title()}] API Request: Create App (Mock)")
        logger.info(f"[{network.title()}] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        mock_response = {
            "status": 0,
            "code": 0,
            "msg": "Success",
            "result": {
                "appCode": "10*****7",
                "name": payload.get("name", "Test App")
            }
        }
        
        logger.info(f"[{network.title()}] Response (Mock): {json.dumps(mock_response, indent=2)}")
        return mock_response
    
    def _is_token_expired(self, token: str) -> bool:
        """Check if JWT token is expired by parsing exp claim
        
        Returns True if token is expired or will expire within 1 hour (23 hours passed)
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("[IronSource] Invalid JWT format (not 3 parts)")
                return True  # Invalid token format, consider expired
            
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            
            # Check exp claim
            exp = claims.get('exp')
            if exp:
                current_time = int(time.time())
                # Token expires in 24 hours, refresh 1 hour before (23 hours passed)
                # So if less than 1 hour (3600 seconds) remaining, consider expired
                time_until_expiry = exp - current_time
                logger.info(f"[IronSource] Token expires in {time_until_expiry} seconds ({time_until_expiry // 3600} hours)")
                
                # Refresh if less than 1 hour remaining
                if time_until_expiry < 3600:
                    logger.info("[IronSource] Token will expire within 1 hour, needs refresh")
                    return True
                else:
                    logger.info("[IronSource] Token is still valid")
                    return False
            
            logger.warning("[IronSource] No exp claim in token, considering expired")
            return True  # No exp claim, consider expired
        except Exception as e:
            logger.warning(f"[IronSource] Error checking token expiration: {str(e)}")
            return True  # On error, consider expired to be safe
    
    def _get_ironsource_token(self) -> Optional[str]:
        """Get IronSource bearer token with automatic refresh
        
        Logic:
        1. Check if bearer_token exists and is not expired (1 hour buffer)
        2. If expired or missing, fetch new token using secret_key and refresh_token
        3. Return valid bearer token
        
        Required: IRONSOURCE_SECRET_KEY, IRONSOURCE_REFRESH_TOKEN
        Optional: IRONSOURCE_BEARER_TOKEN (if exists and valid, use it)
        """
        # Get credentials (required)
        refresh_token = get_env_var("IRONSOURCE_REFRESH_TOKEN")
        secret_key = get_env_var("IRONSOURCE_SECRET_KEY")
        
        # Log what we found
        logger.info(f"[IronSource] Checking credentials...")
        logger.info(f"[IronSource] IRONSOURCE_REFRESH_TOKEN: {'SET' if refresh_token else 'NOT SET'} (length: {len(refresh_token) if refresh_token else 0})")
        logger.info(f"[IronSource] IRONSOURCE_SECRET_KEY: {'SET' if secret_key else 'NOT SET'} (length: {len(secret_key) if secret_key else 0})")
        
        if not refresh_token or not secret_key:
            missing = []
            if not refresh_token:
                missing.append("IRONSOURCE_REFRESH_TOKEN")
            if not secret_key:
                missing.append("IRONSOURCE_SECRET_KEY")
            logger.error(f"[IronSource] Missing required credentials: {', '.join(missing)}")
            logger.error("[IronSource] Please set these in .env file or Streamlit secrets")
            return None
        
        # Check if we have a cached bearer token (optional)
        bearer_token = get_env_var("IRONSOURCE_BEARER_TOKEN") or get_env_var("IRONSOURCE_API_TOKEN")
        
        # If bearer token exists, check if it's still valid (1 hour buffer)
        if bearer_token:
            logger.info("[IronSource] Found existing bearer token, checking expiration...")
            if not self._is_token_expired(bearer_token):
                logger.info("[IronSource] Using existing valid bearer token")
                return bearer_token
            else:
                logger.info("[IronSource] Existing bearer token is expired or will expire soon, refreshing...")
        
        # Fetch new token using secret_key and refresh_token
        logger.info("[IronSource] Fetching new bearer token...")
        new_token = self._refresh_ironsource_token(refresh_token, secret_key)
        
        if new_token:
            logger.info("[IronSource] Successfully obtained new bearer token")
            return new_token
        else:
            logger.error("[IronSource] Failed to obtain bearer token. Check logs above for details.")
            return None
    
    def _get_ironsource_headers(self) -> Optional[Dict[str, str]]:
        """Get IronSource API headers with automatic token refresh (wrapper for compatibility)
        
        This method is called before each API request to ensure we have a valid token.
        Logic:
        1. Get bearer token (with automatic refresh if needed)
        2. Return headers with Authorization: Bearer {token}
        """
        # Use new IronSourceAuth
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.auth.get_headers()
    
    def _refresh_ironsource_token(self, refresh_token: str, secret_key: str) -> Optional[str]:
        """Get IronSource bearer token using refresh token and secret key
        
        API: GET https://platform.ironsrc.com/partners/publisher/auth
        Headers:
            secretkey: IRONSOURCE_SECRET_KEY value
            refreshToken: IRONSOURCE_REFRESH_TOKEN value
        Response: Bearer Token (JWT string, 24 hours valid)
        """
        try:
            url = "https://platform.ironsrc.com/partners/publisher/auth"
            headers = {
                "secretkey": secret_key,
                "refreshToken": refresh_token
            }
            
            logger.info(f"[IronSource] Attempting to get bearer token...")
            logger.info(f"[IronSource] Token URL: GET {url}")
            logger.info(f"[IronSource] Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.info(f"[IronSource] Token response status: {response.status_code}")
            
            if response.status_code == 200:
                # 응답은 따옴표로 감싸진 문자열이므로 제거 (reference code 방식)
                bearer_token = response.text.strip().strip('"')
                
                if bearer_token:
                    logger.info("[IronSource] Bearer token obtained successfully")
                    logger.info(f"[IronSource] Token length: {len(bearer_token)}")
                    logger.info(f"[IronSource] Token (first 50 chars): {bearer_token[:50]}...")
                    logger.info(f"[IronSource] Token valid for: 24 hours")
                    return bearer_token
                else:
                    logger.error("[IronSource] Empty bearer token in response")
                    logger.error(f"[IronSource] Full response text: {response.text}")
                    return None
            else:
                logger.error(f"[IronSource] Token request failed with status {response.status_code}")
                logger.error(f"[IronSource] Response: {response.text[:500]}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[IronSource] Token refresh failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[IronSource] Token error response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[IronSource] Token error response (text): {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[IronSource] Token refresh exception: {str(e)}")
            return None

    
    def _create_ironsource_app(self, payload: Dict) -> Dict:
        """Create app via IronSource API (wrapper for compatibility)"""
        # Use new IronSourceAPI
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.create_app(payload)
    
    def create_unit(self, network: str, payload: Dict, app_key: Optional[str] = None) -> Dict:
        """Create unit via network API
        
        Args:
            network: Network name
            payload: Unit creation payload (for IronSource, this is a single ad unit object)
            app_key: App key (required for IronSource)
        """
        if network == "ironsource":
            # Use new IronSourceAPI
            if self._ironsource_api is None:
                from utils.network_apis.ironsource_api import IronSourceAPI
                self._ironsource_api = IronSourceAPI()
            return self._ironsource_api.create_unit(payload, app_key=app_key)
        elif network == "bigoads":
            # Use new BigOAdsAPI
            if self._bigoads_api is None:
                from utils.network_apis.bigoads_api import BigOAdsAPI
                self._bigoads_api = BigOAdsAPI()
            return self._bigoads_api.create_unit(payload, app_key=app_key)
        elif network == "pangle":
            # Use new PangleAPI
            if self._pangle_api is None:
                from utils.network_apis.pangle_api import PangleAPI
                self._pangle_api = PangleAPI()
            return self._pangle_api.create_unit(payload, app_key=app_key)
        elif network == "mintegral":
            # Use new MintegralAPI
            if self._mintegral_api is None:
                from utils.network_apis.mintegral_api import MintegralAPI
                self._mintegral_api = MintegralAPI()
            return self._mintegral_api.create_unit(payload, app_key=app_key)
        elif network == "inmobi":
            # Use new InMobiAPI
            if self._inmobi_api is None:
                from utils.network_apis.inmobi_api import InMobiAPI
                self._inmobi_api = InMobiAPI()
            return self._inmobi_api.create_unit(payload, app_key=app_key)
        elif network == "fyber":
            # Use new FyberAPI
            if self._fyber_api is None:
                from utils.network_apis.fyber_api import FyberAPI
                self._fyber_api = FyberAPI()
            return self._fyber_api.create_unit(payload, app_key=app_key)
        elif network == "applovin":
            # Use new AppLovinAPI
            if self._applovin_api is None:
                from utils.network_apis.applovin_api import AppLovinAPI
                self._applovin_api = AppLovinAPI()
            return self._applovin_api.create_unit(payload, app_key=app_key)
        elif network == "unity":
            # Unity uses create_ad_units directly, but for consistency:
            # Use new UnityAPI
            if self._unity_api is None:
                from utils.network_apis.unity_api import UnityAPI
                self._unity_api = UnityAPI()
            return self._unity_api.create_unit(payload, app_key=app_key)
        
        # Mock implementation for other networks
        logger.info(f"[{network.title()}] API Request: Create Unit (Mock)")
        logger.info(f"[{network.title()}] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        mock_response = {
            "status": 0,
            "code": 0,
            "msg": "Success",
            "result": {
                "slotCode": "12345-67890",
                "name": payload.get("mediationAdUnitName", payload.get("name", "Test Slot"))
            }
        }
        
        logger.info(f"[{network.title()}] Response (Mock): {json.dumps(mock_response, indent=2)}")
        return mock_response
    
    def _create_ironsource_placements(self, app_key: str, ad_units: List[Dict]) -> Dict:
        """Create placements via IronSource API (wrapper for compatibility)
        
        Args:
            app_key: Application key from IronSource platform
            ad_units: List of ad unit objects to create
        """
        # Use new IronSourceAPI
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.create_placements(app_key, ad_units)
    
    def _update_ironsource_ad_units(self, app_key: str, ad_units: List[Dict]) -> Dict:
        """Update (activate) ad units via IronSource API (wrapper for compatibility)
        
        API: PUT https://platform.ironsrc.com/levelPlay/adUnits/v1/{appKey}
        
        Args:
            app_key: Application key from IronSource platform
            ad_units: List of ad unit objects to update
                Each ad unit must have:
                - mediationAdUnitId (required, uppercase U): ad unit ID from GET request
                - isPaused (optional): false to activate
                - mediationAdUnitName (optional): new name
        """
        # Use new IronSourceAPI
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.update_ad_units(app_key, ad_units)
    
    def _get_ironsource_instances(self, app_key: str) -> Dict:
        """Get instances via IronSource API (wrapper for compatibility)
        
        API: GET https://platform.ironsrc.com/levelPlay/network/instances/v4/{appKey}/
        
        Args:
            app_key: Application key from IronSource platform
        
        Returns:
            Dict with status, code, msg, and result (list of instances)
        """
        # Use new IronSourceAPI
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.get_instances(app_key)
    
    def _generate_bigoads_sign(self, developer_id: str, token: str) -> tuple[str, str]:
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
    
    def _generate_mintegral_signature(self, secret: str, timestamp: int) -> str:
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
    
    def _create_mintegral_app(self, payload: Dict) -> Dict:
        """Create app via Mintegral API"""
        url = "https://dev.mintegral.com/app/open_api_create"
        
        # Mintegral API 인증: SKEY와 SECRET 필요
        skey = get_env_var("MINTEGRAL_SKEY")
        secret = get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        # Reference code uses 'time' (string) instead of 'timestamp' (int)
        current_time = int(time.time())
        signature = self._generate_mintegral_signature(secret, current_time)
        
        # Add authentication parameters to payload
        # Reference code pattern: use 'time' as string parameter
        request_params = payload.copy()
        request_params["skey"] = skey
        request_params["time"] = str(current_time)  # Use 'time' as string, not 'timestamp'
        request_params["sign"] = signature
        
        # Reference code uses application/x-www-form-urlencoded for Media List
        # Create App might also use the same format
        # Try form-urlencoded first (matching Media List pattern)
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
            if key == "sign":
                print(f"[Mintegral]   - {key}: {str(value)[:20]}... (masked)", file=sys.stderr)
            elif key == "skey":
                print(f"[Mintegral]   - {key}: {str(value)[:20]}... (masked)", file=sys.stderr)
            else:
                print(f"[Mintegral]   - {key}: {value} (type: {type(value).__name__})", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        # Also log via logger
        logger.info(f"[Mintegral] API Request: POST {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Mintegral] Request Body: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # Use form-urlencoded (matching Media List API pattern)
            response = requests.post(url, data=request_params, headers=headers, timeout=30)
            
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Print to console for debugging
            print("\n" + "=" * 80, file=sys.stderr)
            print("🟢 [Mintegral] ========== CREATE APP RESPONSE ==========", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(f"[Mintegral] Response Status: {response.status_code}", file=sys.stderr)
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            
            # Also log via logger
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format:
            # Success: {"code": 0, "msg": "Success", ...}
            # Error: {"code": -2007, "msg": "Invalid Params", "traceid": "..."}
            # Check top-level code first
            top_level_code = result.get("code")
            
            # Success: code must be 0 or 200 (positive or zero)
            # Error: code is negative (e.g., -2007, -2004)
            if top_level_code is not None:
                if top_level_code == 0 or top_level_code == 200:
                    # Success
                    print(f"[Mintegral] ✅ Success (code: {top_level_code})", file=sys.stderr)
                    logger.info(f"[Mintegral] ✅ Success (code: {top_level_code})")
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
                    logger.error(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}")
                    return {
                        "status": 1,
                        "code": top_level_code,
                        "msg": error_msg
                    }
            
            # Fallback: if code is not present, check HTTP status
            if response.status_code == 200:
                print(f"[Mintegral] ✅ Success (HTTP 200, no code in response)", file=sys.stderr)
                logger.info(f"[Mintegral] ✅ Success (HTTP 200, no code in response)")
                return {
                    "status": 0,
                    "code": 0,
                    "msg": result.get("msg", "Success"),
                    "result": result.get("result", result.get("data", result))
                }
            else:
                error_msg = result.get("msg") or "Unknown error"
                print(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}", file=sys.stderr)
                logger.error(f"[Mintegral] ❌ Error: HTTP {response.status_code}, msg={error_msg}")
                return {
                    "status": 1,
                    "code": response.status_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Mintegral] API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _get_mintegral_apps(self) -> List[Dict]:
        """Get media list from Mintegral API
        
        API: GET https://dev.mintegral.com/v2/app/open_api_list
        Reference: Uses GET with params (skey, time, sign) and application/x-www-form-urlencoded
        """
        url = "https://dev.mintegral.com/v2/app/open_api_list"
        
        # Mintegral API 인증: SKEY와 SECRET 필요
        skey = get_env_var("MINTEGRAL_SKEY")
        secret = get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            logger.error("[Mintegral] MINTEGRAL_SKEY or MINTEGRAL_SECRET not found")
            return []
        
        # Generate timestamp and signature (use 'time' as parameter name, not 'timestamp')
        current_time = int(time.time())
        signature = self._generate_mintegral_signature(secret, current_time)
        
        # Build request params (GET request with query parameters)
        # Reference code uses: skey, time (not timestamp), sign
        request_params = {
            "skey": skey,
            "time": str(current_time),  # Note: 'time' as string, not 'timestamp'
            "sign": signature
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"  # Reference code uses this
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
        logger.info(f"[Mintegral] API Request: GET {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"[Mintegral] Request Params: {json.dumps(mask_sensitive_data(request_params), indent=2)}")
        
        try:
            # GET request with params (as per reference code)
            response = requests.get(url, headers=headers, params=request_params, timeout=30)
            
            print(f"[Mintegral] Response Status: {response.status_code}", file=sys.stderr)
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Print to console
            print(f"[Mintegral] Response Body: {json.dumps(result, indent=2, ensure_ascii=False)}", file=sys.stderr)
            logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Check response code (reference code: code == 200 means success)
            response_code = result.get("code")
            response_msg = result.get("msg")
            data = result.get("data")
            
            print(f"[Mintegral] Response code: {response_code}", file=sys.stderr)
            print(f"[Mintegral] Response msg: {response_msg}", file=sys.stderr)
            
            if response_code != 200:
                error_msg = response_msg or "Unknown error"
                print(f"[Mintegral] ❌ Error: code={response_code}, msg={error_msg}", file=sys.stderr)
                logger.error(f"[Mintegral] Error: code={response_code}, msg={error_msg}")
                
                # Common error codes from reference
                error_codes = {
                    -2004: "No Access - 인증 실패 (skey, secret, sign 확인)",
                    -2006: "Permission denied - 권한 없음",
                    -2007: "Invalid Params - 잘못된 파라미터"
                }
                if response_code in error_codes:
                    print(f"[Mintegral] 💡 {error_codes[response_code]}", file=sys.stderr)
                
                return []
            
            # Parse response - Reference code: data.lists contains the app list
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
            logger.info(f"[Mintegral] Successfully loaded {len(formatted_apps)} apps from API")
            
            return formatted_apps
            
        except requests.exceptions.RequestException as e:
            print(f"[Mintegral] ❌ API Error (Get Apps): {str(e)}", file=sys.stderr)
            logger.error(f"[Mintegral] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    print(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2, ensure_ascii=False)}", file=sys.stderr)
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    print(f"[Mintegral] Error Response (text): {e.response.text[:500]}", file=sys.stderr)
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text[:500]}")
            return []
        except Exception as e:
            print(f"[Mintegral] ❌ Unexpected Error (Get Apps): {str(e)}", file=sys.stderr)
            logger.error(f"[Mintegral] Unexpected Error (Get Apps): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _create_mintegral_unit(self, payload: Dict) -> Dict:
        """Create ad placement (unit) via Mintegral API"""
        url = "https://dev.mintegral.com/v2/placement/open_api_create"
        
        # Mintegral API 인증: skey, timestamp, sign
        skey = get_env_var("MINTEGRAL_SKEY")
        secret = get_env_var("MINTEGRAL_SECRET")
        
        if not skey or not secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "MINTEGRAL_SKEY and MINTEGRAL_SECRET must be set in .env file"
            }
        
        # Generate timestamp and signature
        # Reference: use 'time' as string parameter, not 'timestamp'
        current_time = int(time.time())
        signature = self._generate_mintegral_signature(secret, current_time)
        
        # Add authentication fields to payload
        # Reference: use 'time' as string, not 'timestamp'
        api_payload = payload.copy()
        api_payload["skey"] = skey
        api_payload["time"] = str(current_time)  # Use 'time' as string, not 'timestamp'
        api_payload["sign"] = signature
        
        # Reference: use application/x-www-form-urlencoded for Mintegral API
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        logger.info(f"[Mintegral] API Request: POST {url}")
        logger.info(f"[Mintegral] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Mintegral] Request Body: {json.dumps(mask_sensitive_data(api_payload), indent=2)}")
        
        try:
            # Use data= instead of json= for form-urlencoded
            response = requests.post(url, data=api_payload, headers=headers, timeout=30)
            
            logger.info(f"[Mintegral] Response Status: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"[Mintegral] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            
            # Mintegral API response format normalization
            # Success: code must be 0 or 200 (positive or zero)
            # Error: code is negative (e.g., -2007, -2004)
            top_level_code = result.get("code")
            
            if top_level_code is not None:
                if top_level_code == 0 or top_level_code == 200:
                    # Success
                    logger.info(f"[Mintegral] ✅ Success (code: {top_level_code})")
                    # Handle empty result object - this is a valid success response
                    result_data = result.get("data")
                    if result_data is None:
                        # If "data" field doesn't exist, check if "result" field exists
                        result_data = result.get("result", {})
                    
                    # If result_data is empty dict and msg indicates empty response, keep it as is
                    # This is a valid success case for Mintegral API
                    msg = result.get("msg", "Success")
                    if not result_data and "empty response" in msg.lower():
                        # This is expected - empty result is valid for Mintegral create unit
                        result_data = {}
                    
                    return {
                        "status": 0,
                        "code": 0,
                        "msg": msg,
                        "result": result_data if result_data else {}
                    }
                else:
                    # Error: negative code or non-zero positive code
                    error_msg = result.get("msg") or result.get("message") or result.get("error") or "Unknown error"
                    logger.error(f"[Mintegral] ❌ Error: code={top_level_code}, msg={error_msg}")
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
            logger.error(f"[Mintegral] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Mintegral] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Mintegral] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_bigoads_app(self, payload: Dict) -> Dict:
        """Create app via BigOAds API"""
        url = "https://www.bigossp.com/open/app/add"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = get_env_var("BIGOADS_DEVELOPER_ID")
        token = get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        # Remove None values from payload to avoid sending null
        cleaned_payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=cleaned_payload, headers=headers)
            
            # Log response even if status code is not 200
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[BigOAds] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[BigOAds] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            response.raise_for_status()
            
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
            logger.error(f"[BigOAds] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_inmobi_app(self, payload: Dict) -> Dict:
        """Create app via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Remove None values and empty strings from payload
        cleaned_payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        
        logger.info(f"[InMobi] API Request: POST {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Payload: {json.dumps(mask_sensitive_data(cleaned_payload), indent=2)}")
        
        try:
            response = requests.post(url, json=cleaned_payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
                result = {"code": response.status_code, "msg": response.text}
            
            # For 400 errors, log detailed error information
            if response.status_code == 400:
                logger.error(f"[InMobi] Bad Request (400) - Full Response: {response.text}")
                print(f"[InMobi] ❌ Bad Request (400)", file=sys.stderr)
                print(f"[InMobi] Response: {response.text}", file=sys.stderr)
                # Try to extract more details from error response
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, dict):
                        error_msg = error_detail.get("message") or error_detail.get("error") or error_detail.get("msg") or str(error_detail)
                        logger.error(f"[InMobi] Error Details: {error_msg}")
                        print(f"[InMobi] Error Details: {error_msg}", file=sys.stderr)
                except:
                    pass
            
            response.raise_for_status()
            
            # InMobi API 응답 형식에 맞게 정규화
            # 응답 형식은 API 문서를 참조하여 수정 필요
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
            logger.error(f"[InMobi] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                    print(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}", file=sys.stderr)
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
                    print(f"[InMobi] Error Response (text): {e.response.text}", file=sys.stderr)
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _get_fyber_access_token(self) -> Optional[str]:
        """Get Fyber (DT) Access Token (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use FyberAPI.get_access_token() directly.
        
        Returns:
            Access token string or None if failed
        """
        if self._fyber_api is None:
            from utils.network_apis.fyber_api import FyberAPI
            self._fyber_api = FyberAPI()
        return self._fyber_api.get_access_token()
    
    def _create_fyber_app(self, payload: Dict) -> Dict:
        """Create app via Fyber (DT) API"""
        url = "https://console.fyber.com/api/management/v1/app"
        
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        # Fyber API 인증 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        logger.info(f"[Fyber] API Request: POST {url}")
        logger.info(f"[Fyber] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Fyber] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Fyber] Response Text: {response.text}")
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
                        logger.error("[Fyber] 💡 카테고리 오류:")
                        logger.error("[Fyber]   → 선택한 카테고리가 플랫폼에 맞지 않습니다.")
                        logger.error("[Fyber]   → Android와 iOS는 서로 다른 카테고리를 사용합니다.")
                        logger.error(f"[Fyber]   → 에러 메시지: {error_msg[:200]}...")
                
                return {
                    "status": 1,
                    "code": error_code,
                    "msg": error_msg
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] API Error (Create App): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_unity_ad_units(self, project_id: str, store_name: str, ad_units_payload: List[Dict]) -> Dict:
        """Create Unity ad units (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use UnityAPI.create_ad_units directly.
        
        Args:
            project_id: Unity project ID
            store_name: Store name ("apple" or "google")
            ad_units_payload: List of ad unit objects to create
            
        Returns:
            API response dict
        """
        if self._unity_api is None:
            from utils.network_apis.unity_api import UnityAPI
            self._unity_api = UnityAPI()
        return self._unity_api.create_ad_units(project_id, store_name, ad_units_payload)
    
    def _update_unity_ad_units(self, project_id: str, store_name: str, ad_units_payload: Dict) -> Dict:
        """Update Unity ad units (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use UnityAPI.update_ad_units directly.
        """
        if self._unity_api is None:
            from utils.network_apis.unity_api import UnityAPI
            self._unity_api = UnityAPI()
        return self._unity_api.update_ad_units(project_id, store_name, ad_units_payload)

    def _create_unity_placements(self, project_id: str, store_name: str, ad_unit_id: str, placements_payload: List[Dict]) -> Dict:
        """Create Unity placements (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use UnityAPI.create_placements directly.
        """
        if self._unity_api is None:
            from utils.network_apis.unity_api import UnityAPI
            self._unity_api = UnityAPI()
        return self._unity_api.create_placements(project_id, store_name, ad_unit_id, placements_payload)
    
    def _get_unity_ad_units(self, project_id: str) -> Dict:
        """Get Unity ad units (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use UnityAPI.get_ad_units directly.
        """
        if self._unity_api is None:
            from utils.network_apis.unity_api import UnityAPI
            self._unity_api = UnityAPI()
        return self._unity_api.get_ad_units(project_id)

    def _create_fyber_unit(self, payload: Dict) -> Dict:
        """Create placement (unit) via Fyber (DT) API
        
        API: POST https://console.fyber.com/api/management/v1/placement
        """
        url = "https://console.fyber.com/api/management/v1/placement"
        
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "Failed to obtain Fyber access token. Please check DT_CLIENT_ID and DT_CLIENT_SECRET in .env file or Streamlit secrets."
            }
        
        # Fyber API 인증 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        logger.info(f"[Fyber] API Request: POST {url}")
        logger.info(f"[Fyber] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[Fyber] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[Fyber] Response Text: {response.text}")
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
            logger.error(f"[Fyber] API Error (Create Placement): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    def _create_bigoads_unit(self, payload: Dict) -> Dict:
        """Create unit (slot) via BigOAds API"""
        url = "https://www.bigossp.com/open/slot/add"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = get_env_var("BIGOADS_DEVELOPER_ID")
        token = get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set in .env file"
            }
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
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
        logger.info(f"[BigOAds] ========== CREATE UNIT REQUEST ==========")
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(masked_headers, indent=2)}")
        logger.info(f"[BigOAds] Request Payload (full): {json.dumps(payload, indent=2, ensure_ascii=False)}")
        logger.info(f"[BigOAds] Payload keys: {list(payload.keys())}")
        logger.info(f"[BigOAds] Payload values: {list(payload.values())}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
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
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            logger.info(f"[BigOAds] Response Headers: {dict(response.headers)}")
            if "result" in locals():
                logger.info(f"[BigOAds] Response Body (JSON): {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # BigOAds API 응답 형식에 맞게 정규화
            if result.get("code") == 0 or result.get("status") == 0:
                print(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}", file=sys.stderr)
                logger.info(f"[BigOAds] ✅ Success: {result.get('msg', 'Success')}")
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
                logger.error(f"[BigOAds] ❌ Error: {error_code} - {error_msg}")
                logger.error(f"[BigOAds] Full error response: {json.dumps(result, indent=2, ensure_ascii=False)}")
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
            logger.error(f"[BigOAds] ❌ API Error (Create Unit): {str(e)}")
            logger.error(f"[BigOAds] Error type: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[BigOAds] Response Status: {e.response.status_code}")
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response (JSON): {json.dumps(error_body, indent=2, ensure_ascii=False)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text[:500]}")
            
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": f"Error creating unit: {str(e)}"
            }
    
    def _create_inmobi_unit(self, payload: Dict) -> Dict:
        """Create unit (placement) via InMobi API"""
        url = "https://publisher.inmobi.com/rest/api/v1/placements"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            return {
                "status": 1,
                "code": "AUTH_ERROR",
                "msg": "INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set in .env file or Streamlit secrets"
            }
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        logger.info(f"[InMobi] API Request: POST {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Payload: {json.dumps(mask_sensitive_data(payload), indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log response even if status code is not 200
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
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
            logger.error(f"[InMobi] API Error (Create Unit): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return {
                "status": 1,
                "code": "API_ERROR",
                "msg": str(e)
            }
    
    
    def _get_ironsource_apps(self, app_key: Optional[str] = None) -> List[Dict]:
        """Get IronSource applications list from API (wrapper for compatibility)
        
        API: GET https://platform.ironsrc.com/partners/publisher/applications/v6
        Headers:
            Authorization: Bearer {token}
            Content-Type: application/json
        Query Parameters (optional):
            platform: "ios" or "android" (from IRONSOURCE_PLATFORM env var)
            appStatus: "Active" or "archived" (from IRONSOURCE_APP_STATUS env var)
            appKey: Specific app key to filter (if provided)
        
        Args:
            app_key: Optional app key to filter by. If provided, only returns that app.
        """
        # Use new IronSourceAPI
        if self._ironsource_api is None:
            from utils.network_apis.ironsource_api import IronSourceAPI
            self._ironsource_api = IronSourceAPI()
        return self._ironsource_api.get_apps(app_key=app_key)
    
    def _get_bigoads_apps(self) -> List[Dict]:
        """Get apps list from BigOAds API"""
        # Add delay to avoid QPS limit (BigOAds has strict rate limiting)
        import time
        time.sleep(0.5)  # 500ms delay to avoid QPS limit
        
        url = "https://www.bigossp.com/open/app/list"
        
        # BigOAds API 인증: developerId와 token 필요
        developer_id = get_env_var("BIGOADS_DEVELOPER_ID")
        token = get_env_var("BIGOADS_TOKEN")
        
        if not developer_id or not token:
            logger.error("[BigOAds] BIGOADS_DEVELOPER_ID and BIGOADS_TOKEN must be set")
            return []
        
        # Generate signature
        sign, timestamp = self._generate_bigoads_sign(developer_id, token)
        
        headers = {
            "Content-Type": "application/json",
            "X-BIGO-DeveloperId": developer_id,
            "X-BIGO-Sign": sign
        }
        
        # Request payload
        payload = {
            "pageNo": 1,
            "pageSize": 10
        }
        
        logger.info(f"[BigOAds] API Request: POST {url}")
        logger.info(f"[BigOAds] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[BigOAds] Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            logger.info(f"[BigOAds] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[BigOAds] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[BigOAds] Response Text: {response.text}")
                return []
            
            response.raise_for_status()
            
            # BigOAds API 응답 형식에 맞게 처리
            # Response format: {"code": "100", "status": 0, "result": {"list": [...], "total": 12}}
            code = result.get("code")
            status = result.get("status")
            
            # Success: code == "100" or status == 0
            if code == "100" or status == 0:
                # Extract apps from result.list
                result_data = result.get("result", {})
                apps_list = result_data.get("list", [])
                
                logger.info(f"[BigOAds] Extracted {len(apps_list)} apps from API response (total: {result_data.get('total', 0)})")
                
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
                
                logger.info(f"[BigOAds] Converted to {len(apps)} apps in standard format")
                return apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"[BigOAds] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[BigOAds] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[BigOAds] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[BigOAds] Error Response (text): {e.response.text}")
            return []
    
    def _get_inmobi_apps(self) -> List[Dict]:
        """Get apps list from InMobi API
        
        API: GET https://publisher.inmobi.com/rest/api/v2/apps
        Headers: x-client-id, x-account-id, x-client-secret
        """
        url = "https://publisher.inmobi.com/rest/api/v2/apps"
        
        # InMobi API 인증: x-client-id, x-account-id, x-client-secret 헤더 사용
        username = get_env_var("INMOBI_USERNAME")  # x-client-id (email ID)
        account_id = get_env_var("INMOBI_ACCOUNT_ID")  # x-account-id (Account ID)
        client_secret = get_env_var("INMOBI_CLIENT_SECRET")  # x-client-secret (API key)
        
        if not username or not account_id or not client_secret:
            logger.error("[InMobi] INMOBI_USERNAME, INMOBI_ACCOUNT_ID, and INMOBI_CLIENT_SECRET must be set")
            return []
        
        # InMobi 인증 헤더 설정
        headers = {
            "x-client-id": username,
            "x-account-id": account_id,
            "x-client-secret": client_secret,
            "Accept": "application/json",
        }
        
        # Query parameters
        params = {
            "pageNum": 1,
            "pageLength": 10,
            "status": "ACTIVE",
        }
        
        logger.info(f"[InMobi] API Request: GET {url}")
        logger.info(f"[InMobi] Request Headers: {json.dumps(mask_sensitive_data(headers), indent=2)}")
        logger.info(f"[InMobi] Request Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            logger.info(f"[InMobi] Response Status: {response.status_code}")
            
            try:
                result = response.json()
                logger.info(f"[InMobi] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
            except:
                logger.error(f"[InMobi] Response Text: {response.text}")
                return []
            
            response.raise_for_status()
            
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
                    logger.error(f"[InMobi] Unexpected response format: {type(result)}")
                    return []
                
                logger.info(f"[InMobi] Extracted {len(apps)} apps from API response (total: {total})")
                
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
                
                logger.info(f"[InMobi] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"[InMobi] API Error (Get Apps): {error_msg}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[InMobi] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[InMobi] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[InMobi] Error Response (text): {e.response.text}")
            return []
    
    def _get_fyber_apps(self, publisher_id: Optional[int] = None, app_id: Optional[int] = None) -> List[Dict]:
        """Get apps list from Fyber (DT) API
        
        API: GET https://console.fyber.com/api/management/v1/app?publisherId={publisherId}
        or GET https://console.fyber.com/api/management/v1/app?appId={appId}
        
        Args:
            publisher_id: Publisher ID (optional)
            app_id: App ID (optional)
        """
        # Get access token
        access_token = self._get_fyber_access_token()
        if not access_token:
            logger.error("[Fyber] Failed to get access token for get_apps")
            return []
        
        # Get publisher_id or app_id from environment if not provided
        if not publisher_id and not app_id:
            publisher_id_str = get_env_var("FYBER_PUBLISHER_ID") or get_env_var("DT_PUBLISHER_ID")
            app_id_str = get_env_var("FYBER_APP_ID") or get_env_var("DT_APP_ID")
            
            if app_id_str:
                try:
                    app_id = int(app_id_str)
                except ValueError:
                    logger.warning(f"[Fyber] Invalid FYBER_APP_ID: {app_id_str}")
            elif publisher_id_str:
                try:
                    publisher_id = int(publisher_id_str)
                except ValueError:
                    logger.warning(f"[Fyber] Invalid FYBER_PUBLISHER_ID: {publisher_id_str}")
        
        if not publisher_id and not app_id:
            logger.error("[Fyber] publisher_id or app_id is required for get_apps")
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
        
        logger.info(f"[Fyber] Get Apps API Request: GET {url}")
        logger.info(f"[Fyber] Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            logger.info(f"[Fyber] Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[Fyber] Response Body: {json.dumps(mask_sensitive_data(result), indent=2)}")
                
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
                
                logger.info(f"[Fyber] Converted to {len(formatted_apps)} apps in standard format")
                return formatted_apps
            else:
                logger.error(f"[Fyber] Failed to get apps. Status: {response.status_code}")
                logger.error(f"[Fyber] Response: {response.text}")
                
                if response.status_code == 401:
                    logger.error("[Fyber] 💡 인증 오류: Access Token이 만료되었거나 유효하지 않습니다.")
                elif response.status_code == 403:
                    logger.error("[Fyber] 💡 권한 오류: Publisher ID 또는 App ID에 대한 접근 권한이 없습니다.")
                elif response.status_code == 404:
                    logger.error("[Fyber] 💡 리소스를 찾을 수 없음: Publisher ID 또는 App ID가 올바른지 확인해주세요.")
                
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Fyber] API Error (Get Apps): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    logger.error(f"[Fyber] Error Response: {json.dumps(error_body, indent=2)}")
                except:
                    logger.error(f"[Fyber] Error Response (text): {e.response.text}")
            return []
    
    def _get_vungle_jwt_token(self) -> Optional[str]:
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
                
                # Check for error messages
                if "messages" in result:
                    error_msg = result.get("messages", [])
                    error_code = result.get("code")
                    logger.error(f"[Vungle] Error getting JWT token: {error_msg} (code: {error_code})")
                    return None
                
                jwt_token = result.get("token")
                if jwt_token:
                    logger.info("[Vungle] JWT token obtained successfully")
                    return jwt_token
                else:
                    logger.error("[Vungle] JWT token not found in response")
                    return None
            else:
                logger.error(f"[Vungle] Failed to get JWT token: {response.status_code} - {response.text[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[Vungle] Error requesting JWT token: {str(e)}")
            return None
    
    def _get_vungle_placements(self) -> List[Dict]:
        """Get all placements from Vungle API
        
        API: GET https://publisher-api.vungle.com/api/v1/placements
        
        Returns:
            List of placement dicts (each contains app and unit info)
        """
        jwt_token = self._get_vungle_jwt_token()
        if not jwt_token:
            logger.error("[Vungle] Failed to get JWT token for placements")
            return []
        
        base_url = "https://publisher-api.vungle.com/api/v1"
        placements_url = f"{base_url}/placements"
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        logger.info(f"[Vungle] Fetching all placements from {placements_url}")
        
        try:
            response = requests.get(placements_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response - can be list or dict
                placements = []
                if isinstance(result, list):
                    placements = result
                elif isinstance(result, dict):
                    placements = result.get("data", result.get("placements", result.get("list", [])))
                    if not isinstance(placements, list):
                        placements = []
                
                logger.info(f"[Vungle] Retrieved {len(placements)} placements")
                return placements
            else:
                logger.error(f"[Vungle] Failed to get placements: {response.status_code} - {response.text[:200]}")
                if response.status_code == 401:
                    logger.error("[Vungle] Authentication failed - JWT token may be expired")
                elif response.status_code == 403:
                    logger.error("[Vungle] Permission denied")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[Vungle] Error fetching placements: {str(e)}")
            return []
    
    def _get_unity_projects(self) -> List[Dict]:
        """Get Unity projects (wrapper for compatibility)
        
        Note: This is a wrapper method for backward compatibility.
        New code should use UnityAPI.get_apps directly.
        """
        if self._unity_api is None:
            from utils.network_apis.unity_api import UnityAPI
            self._unity_api = UnityAPI()
        return self._unity_api.get_apps(app_key=None)
    
    
    def get_apps(self, network: str, app_key: Optional[str] = None) -> List[Dict]:
        """Get apps list from network
        
        Args:
            network: Network name (e.g., "bigoads", "ironsource", "fyber", "vungle")
            app_key: Optional app key to filter by (for IronSource)
        """
        if network == "bigoads":
            # Use new BigOAdsAPI
            if self._bigoads_api is None:
                from utils.network_apis.bigoads_api import BigOAdsAPI
                self._bigoads_api = BigOAdsAPI()
            return self._bigoads_api.get_apps(app_key=app_key)
        elif network == "ironsource":
            # Use new IronSourceAPI
            if self._ironsource_api is None:
                from utils.network_apis.ironsource_api import IronSourceAPI
                self._ironsource_api = IronSourceAPI()
            return self._ironsource_api.get_apps(app_key=app_key)
        elif network == "mintegral":
            # Use new MintegralAPI
            if self._mintegral_api is None:
                from utils.network_apis.mintegral_api import MintegralAPI
                self._mintegral_api = MintegralAPI()
            return self._mintegral_api.get_apps(app_key=app_key)
        elif network == "inmobi":
            # Use new InMobiAPI
            if self._inmobi_api is None:
                from utils.network_apis.inmobi_api import InMobiAPI
                self._inmobi_api = InMobiAPI()
            return self._inmobi_api.get_apps(app_key=app_key)
        elif network == "fyber":
            # Use new FyberAPI
            if self._fyber_api is None:
                from utils.network_apis.fyber_api import FyberAPI
                self._fyber_api = FyberAPI()
            return self._fyber_api.get_apps(app_key=app_key)
        elif network == "vungle":
            # For Vungle, placements contain both app and unit info
            # Extract unique apps from placements
            placements = self._get_vungle_placements()
            apps_dict = {}
            for placement in placements:
                app_id = placement.get("applicationId")
                if app_id and app_id not in apps_dict:
                    apps_dict[app_id] = {
                        "appId": app_id,
                        "name": placement.get("applicationName", ""),
                        "platform": placement.get("platform", ""),
                        "packageName": placement.get("packageName", ""),
                        "bundleId": placement.get("bundleId", "")
                    }
            return list(apps_dict.values())
        elif network == "unity":
            # Use new UnityAPI
            if self._unity_api is None:
                from utils.network_apis.unity_api import UnityAPI
                self._unity_api = UnityAPI()
            # Unity does not use app_key, but we pass it for interface consistency
            return self._unity_api.get_apps(app_key=None)
        elif network == "pangle":
            # Use new PangleAPI
            if self._pangle_api is None:
                from utils.network_apis.pangle_api import PangleAPI
                self._pangle_api = PangleAPI()
            return self._pangle_api.get_apps(app_key=app_key)
        
        # Mock implementation for other networks
        return [
            {
                "appCode": "10*****7",
                "name": "MyTestApp",
                "platform": "Android",
                "status": "Active"
            },
            {
                "appCode": "10*****8",
                "name": "AnotherApp",
                "platform": "iOS",
                "status": "Active"
            }
        ]
    
    def get_units(self, network: str, app_code: str) -> List[Dict]:
        """Get units list for an app"""
        if network == "pangle":
            # Use new PangleAPI
            if self._pangle_api is None:
                from utils.network_apis.pangle_api import PangleAPI
                self._pangle_api = PangleAPI()
            return self._pangle_api.get_units(app_code=app_code)
        
        # Mock implementation for other networks
        return [
            {
                "slotCode": "12345-678",
                "name": "TestSlot1",
                "adType": "Native",
                "auctionType": "Waterfall"
            },
            {
                "slotCode": "12345-679",
                "name": "TestSlot2",
                "adType": "Banner",
                "auctionType": "Client Bidding"
            }
        ]

# Global instance
_network_manager = None


def get_network_manager():
    """Get or create network manager instance"""
    global _network_manager
    if _network_manager is None:
        # In real implementation, initialize from BE/services/ad_network_manager.py
        # For now, use mock
        _network_manager = MockNetworkManager()
    return _network_manager

