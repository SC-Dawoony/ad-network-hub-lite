"""Vungle (Liftoff) network configuration"""
from typing import Dict, List, Tuple, Optional
from .base_config import NetworkConfig, Field, ConditionalField


class VungleConfig(NetworkConfig):
    """Vungle (Liftoff) network configuration"""
    
    @property
    def network_name(self) -> str:
        return "vungle"
    
    @property
    def display_name(self) -> str:
        return "Vungle (Liftoff)"
    
    def get_app_creation_fields(self) -> List[Field]:
        """Get fields for app creation
        
        Vungle supports separate app creation for iOS and Android
        """
        return [
            Field(
                name="name",
                field_type="text",
                required=True,
                label="App Name*",
                placeholder="Enter app name",
                help_text="Name of the app"
            ),
            # Platform-specific fields will be populated from store info
            Field(
                name="platform",
                field_type="hidden",
                required=False,
                label="Platform",
                default="ios"
            ),
        ]
    
    def get_unit_creation_fields(self, ad_type: Optional[str] = None) -> List[Field]:
        """Get fields for unit (placement) creation
        
        Vungle placements are created with:
        - application: vungleAppId (from app creation response)
        - name: auto-generated placement name
        - type: "rewarded" | "interstitial" | "banner"
        - allowEndCards: true
        - isHBParticipation: true
        """
        return []
    
    def validate_app_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate app creation data"""
        if not data.get("name"):
            return False, "App name is required"
        if not data.get("platform"):
            return False, "Platform is required"
        if data.get("platform") not in ["ios", "android"]:
            return False, "Platform must be 'ios' or 'android'"
        return True, ""
    
    def validate_unit_data(self, data: Dict) -> Tuple[bool, str]:
        """Validate unit creation data"""
        if not data.get("application"):
            return False, "Application (vungleAppId) is required"
        if not data.get("name"):
            return False, "Placement name is required"
        if not data.get("type"):
            return False, "Placement type is required"
        valid_types = ["rewarded", "interstitial", "banner"]
        if data.get("type") not in valid_types:
            return False, f"Type must be one of: {', '.join(valid_types)}"
        return True, ""
    
    def build_app_payload(self, form_data: Dict, platform: Optional[str] = None) -> Dict:
        """Build API payload for app creation
        
        API: POST /applications
        Payload structure:
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
        
        Default values:
        - category: "Games"
        - isPaid: false
        - isManual: false
        - isCoppa: true
        
        Args:
            form_data: Form data dictionary
            platform: Optional platform string ("iOS" or "Android") - if provided, extracts platform-specific data
        """
        # Determine platform
        if platform:
            # Convert "iOS" or "Android" to "ios" or "android"
            platform_lower = platform.lower()
            if platform_lower == "ios":
                platform_value = "ios"
                store_id = form_data.get("ios_store_id", form_data.get("iosAppId", ""))
                store_url = form_data.get("ios_store_url", form_data.get("iosStoreUrl", ""))
                name = form_data.get("ios_name", form_data.get("name", ""))
            else:  # Android
                platform_value = "android"
                store_id = form_data.get("android_store_id", form_data.get("androidPackageName", ""))
                store_url = form_data.get("android_store_url", form_data.get("androidStoreUrl", ""))
                name = form_data.get("android_name", form_data.get("name", ""))
        else:
            # Use form_data directly
            platform_value = form_data.get("platform", "ios")
            store_id = form_data.get("store_id", "")
            store_url = form_data.get("store_url", "")
            name = form_data.get("name", "")
        
        thumbnail = form_data.get("thumbnail", "")  # Optional
        
        payload = {
            "platform": platform_value,
            "name": name,
            "store": {
                "id": store_id,
                "category": "Games",  # Fixed default value
                "isPaid": False,  # Fixed default value
                "isManual": False,  # Fixed default value
                "url": store_url,
            },
            "isCoppa": True  # Fixed default value
        }
        
        # Add thumbnail only if provided
        if thumbnail:
            payload["store"]["thumbnail"] = thumbnail
        
        return payload
    
    def build_unit_payload(self, form_data: Dict) -> Dict:
        """Build API payload for unit (placement) creation
        
        API: POST /placements
        Payload structure:
        {
            "application": "vungleAppId",
            "name": "placement_name",
            "type": "rewarded" | "interstitial" | "banner",
            "allowEndCards": true,
            "isHBParticipation": true
        }
        
        Fixed values:
        - allowEndCards: true
        - isHBParticipation: true (In-app bidding)
        
        Note: adRefreshDuration is optional and only needed for banner placements (>= 10)
        """
        payload = {
            "application": form_data.get("application"),  # vungleAppId
            "name": form_data.get("name"),  # Placement name (auto-generated)
            "type": form_data.get("type"),  # "rewarded" | "interstitial" | "banner"
            "allowEndCards": True,  # Fixed value
            "isHBParticipation": True  # Fixed value (In-app bidding)
        }
        
        # Add adRefreshDuration only for banner placements (optional, but if provided must be >= 10)
        if form_data.get("type") == "banner" and form_data.get("adRefreshDuration"):
            ad_refresh_duration = form_data.get("adRefreshDuration")
            if isinstance(ad_refresh_duration, (int, float)) and ad_refresh_duration >= 10:
                payload["adRefreshDuration"] = int(ad_refresh_duration)
        
        return payload

