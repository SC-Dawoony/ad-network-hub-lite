"""Payload Preview Logic - Generate preview data"""
import logging
from typing import Dict, List, Tuple, Optional
from network_configs import get_network_config
from services.app_creation import map_store_info_to_network_params
from utils.network_manager import get_network_manager
from components.create_app_helpers import generate_slot_name

logger = logging.getLogger(__name__)


def generate_preview_data(
    selected_networks: List[str],
    available_networks: Dict[str, str],
    store_info_ios: Optional[Dict] = None,
    store_info_android: Optional[Dict] = None,
    ios_ad_unit_identifier: Optional[Dict] = None
) -> Tuple[Dict, bool]:
    """Generate preview data for selected networks
    
    Args:
        selected_networks: List of selected network keys
        available_networks: Dictionary of network keys to display names
        store_info_ios: iOS app store information
        store_info_android: Android app store information
        ios_ad_unit_identifier: User-selected identifier for ad unit naming (dict with "value" key)
    
    Returns:
        Tuple of (preview_data dict, has_errors bool)
    """
    preview_data = {}
    has_errors = False
    
    for network_key in selected_networks:
        network_display = available_networks[network_key]
        config = get_network_config(network_key)
        
        # AppLovin: Skip app creation, show info message
        if network_key == "applovin":
            preview_data[network_key] = {
                "display": network_display,
                "skip_app_creation": True,
                "info_message": "AppLovin은 API를 통한 앱 생성 기능을 지원하지 않습니다. 대시보드에서 앱을 생성한 후, 아래 'Create Unit' 섹션에서 Ad Unit을 생성할 수 있습니다."
            }
            continue
        
        # Map store info to network parameters
        mapped_params = map_store_info_to_network_params(
            store_info_ios,
            store_info_android,
            network_key,
            config
        )
        
        # Build payloads for preview (check required fields during payload building)
        payloads = {}
        
        # Handle networks that support both iOS and Android
        if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "pangle", "vungle"]:
            if store_info_android:
                try:
                    android_payload = config.build_app_payload(mapped_params, platform="Android")
                    payloads["Android"] = android_payload
                except Exception as e:
                    payloads["Android"] = {"error": str(e)}
                    has_errors = True
            
            if store_info_ios:
                try:
                    ios_payload = config.build_app_payload(mapped_params, platform="iOS")
                    payloads["iOS"] = ios_payload
                except Exception as e:
                    payloads["iOS"] = {"error": str(e)}
                    has_errors = True
        elif network_key == "mintegral":
            # Mintegral requires separate payloads for iOS and Android (single os field)
            # Check required fields per platform
            missing_required_android = []
            missing_required_ios = []
            
            if store_info_android:
                # Check Android required fields
                android_params = mapped_params.copy()
                android_params["os"] = "ANDROID"
                android_params["package"] = mapped_params.get("android_package", "")
                android_params["store_url"] = mapped_params.get("android_store_url", "")
                
                required_fields = config.get_app_creation_fields()
                for field in required_fields:
                    if field.required and field.name not in android_params:
                        from config.base_config import ConditionalField
                        if isinstance(field, ConditionalField):
                            if field.should_show(android_params):
                                missing_required_android.append(field.label or field.name)
                        else:
                            missing_required_android.append(field.label or field.name)
                
                if missing_required_android:
                    payloads["Android"] = {"error": f"필수 필드 누락: {', '.join(missing_required_android)}"}
                    has_errors = True
                else:
                    try:
                        android_payload = config.build_app_payload(android_params)
                        payloads["Android"] = android_payload
                    except Exception as e:
                        payloads["Android"] = {"error": str(e)}
                        has_errors = True
            
            if store_info_ios:
                # Check iOS required fields
                ios_params = mapped_params.copy()
                ios_params["os"] = "IOS"
                ios_params["package"] = mapped_params.get("ios_package", "")
                ios_params["store_url"] = mapped_params.get("ios_store_url", "")
                
                required_fields = config.get_app_creation_fields()
                for field in required_fields:
                    if field.required and field.name not in ios_params:
                        from config.base_config import ConditionalField
                        if isinstance(field, ConditionalField):
                            if field.should_show(ios_params):
                                missing_required_ios.append(field.label or field.name)
                        else:
                            missing_required_ios.append(field.label or field.name)
                
                if missing_required_ios:
                    payloads["iOS"] = {"error": f"필수 필드 누락: {', '.join(missing_required_ios)}"}
                    has_errors = True
                else:
                    try:
                        ios_payload = config.build_app_payload(ios_params)
                        payloads["iOS"] = ios_payload
                    except Exception as e:
                        payloads["iOS"] = {"error": str(e)}
                        has_errors = True
        else:
            # Single platform or other networks - check required fields
            required_fields = config.get_app_creation_fields()
            missing_required = []
            for field in required_fields:
                if field.required and field.name not in mapped_params:
                    from config.base_config import ConditionalField
                    if isinstance(field, ConditionalField):
                        if field.should_show(mapped_params):
                            missing_required.append(field.label or field.name)
                    else:
                        missing_required.append(field.label or field.name)
            
            if missing_required:
                preview_data[network_key] = {
                    "display": network_display,
                    "error": f"필수 필드 누락: {', '.join(missing_required)}",
                    "params": mapped_params
                }
                has_errors = True
            else:
                try:
                    payload = config.build_app_payload(mapped_params)
                    payloads["default"] = payload
                except Exception as e:
                    payloads["default"] = {"error": str(e)}
                    has_errors = True
        
        # Only add to preview_data if not already added (for error case in else branch)
        if network_key not in preview_data or "error" not in preview_data.get(network_key, {}):
            # Prepare ad unit payloads for preview (with placeholder for appCode)
            unit_payloads = {}
            if config.supports_create_unit():
                network_manager = get_network_manager()
                
                # Get app name
                app_name = None
                if store_info_ios:
                    app_name = store_info_ios.get("name", "")
                if not app_name and store_info_android:
                    app_name = store_info_android.get("name", "")
                
                # Get user-selected identifier
                selected_app_match_name = None
                if ios_ad_unit_identifier:
                    selected_app_match_name = ios_ad_unit_identifier.get("value", None)
                
                # Generate unit payloads for each platform
                for platform_key, platform_payload in payloads.items():
                    if isinstance(platform_payload, dict) and "error" in platform_payload:
                        continue
                    
                    platform_str = platform_key if platform_key != "default" else "Android"
                    platform_lower = platform_str.lower()
                    
                    if platform_lower == "android":
                        # For Android, use selected App match name if available, otherwise use package name
                        if selected_app_match_name:
                            # Use selected App match name (already lowercase)
                            pkg_name = selected_app_match_name
                            bundle_id = ""
                        else:
                            # Fallback to package name
                            pkg_name = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("androidBundle", ""))))
                            if not pkg_name and network_key == "inmobi" and store_info_android:
                                pkg_name = store_info_android.get("package_name", "")
                            bundle_id = ""
                        
                        # Always use selected App match name for unit name generation (for consistency)
                        android_package_for_unit = selected_app_match_name
                    else:  # iOS
                        pkg_name = ""
                        # For Vungle iOS, avoid using iTunesId (ios_store_id might be iTunesId)
                        # Use bundle_id directly from store_info_ios
                        if network_key == "vungle" and store_info_ios:
                            bundle_id = store_info_ios.get("bundle_id", "")  # Use bundle_id, not iTunesId
                        else:
                            bundle_id = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("iosBundle", ""))))
                            if not bundle_id and network_key == "inmobi" and store_info_ios:
                                bundle_id = store_info_ios.get("bundle_id", "")
                        
                        # For iOS, prioritize user-selected identifier (App match name)
                        # If not selected, use Android package name
                        if selected_app_match_name:
                            android_package_for_unit = selected_app_match_name
                        else:
                            # Fallback: try to use Android package name if available
                            android_package_for_unit = mapped_params.get("android_package", mapped_params.get("androidPkgName", ""))
                            if android_package_for_unit and '.' in android_package_for_unit:
                                android_package_for_unit = android_package_for_unit.split('.')[-1].lower()
                    
                    # Generate unit payloads for RV, IS, BN
                    platform_unit_payloads = {}
                    for slot_type in ["rv", "is", "bn"]:
                        slot_name = generate_slot_name(
                            pkg_name,
                            platform_lower,
                            slot_type,
                            network_key,
                            bundle_id=bundle_id,
                            network_manager=network_manager,
                            app_name=app_name,
                            android_package_name=android_package_for_unit if android_package_for_unit else None
                        )
                        
                        if slot_name:
                            # Build unit payload with placeholder for appCode/appId/site_id
                            # Each network has different required parameters
                            if network_key == "bigoads":
                                unit_payload = {
                                    "appCode": "{APP_CODE}",  # Placeholder
                                    "name": slot_name,
                                }
                                if slot_type.lower() == "rv":
                                    unit_payload.update({"adType": 4, "auctionType": 3, "musicSwitch": 1})
                                elif slot_type.lower() == "is":
                                    unit_payload.update({"adType": 3, "auctionType": 3, "musicSwitch": 1})
                                elif slot_type.lower() == "bn":
                                    unit_payload.update({"adType": 2, "auctionType": 3, "bannerAutoRefresh": 2, "bannerSize": [2]})
                            elif network_key == "ironsource":
                                # IronSource: mediationAdUnitName, adFormat
                                ad_format_map = {
                                    "rv": "rewarded",
                                    "is": "interstitial",
                                    "bn": "banner"
                                }
                                ad_format = ad_format_map.get(slot_type.lower(), "rewarded")
                                unit_payload = {
                                    "mediationAdUnitName": slot_name,
                                    "adFormat": ad_format,
                                }
                                # Add reward for rewarded format
                                if ad_format == "rewarded":
                                    unit_payload["reward"] = {
                                        "rewardItemName": "Reward",
                                        "rewardAmount": 1
                                    }
                            elif network_key == "pangle":
                                # Pangle: site_id, bidding_type, ad_slot_type
                                ad_slot_type_map = {
                                    "rv": 5,  # Rewarded Video
                                    "is": 6,  # Interstitial
                                    "bn": 2   # Banner
                                }
                                ad_slot_type = ad_slot_type_map.get(slot_type.lower(), 5)
                                unit_payload = {
                                    "site_id": "{APP_CODE}",  # Placeholder
                                    "bidding_type": 1,  # Default: Bidding
                                    "ad_slot_type": ad_slot_type,
                                }
                                # Add type-specific fields
                                if ad_slot_type == 5:  # Rewarded Video
                                    unit_payload.update({
                                        "render_type": 1,
                                        "orientation": 1,
                                        "reward_is_callback": 0,
                                        "reward_name": "Reward",
                                        "reward_count": 1,
                                    })
                                elif ad_slot_type == 6:  # Interstitial
                                    unit_payload.update({
                                        "render_type": 1,
                                        "orientation": 1,
                                    })
                                elif ad_slot_type == 2:  # Banner
                                    unit_payload.update({
                                        "render_type": 1,
                                        "slide_banner": 1,
                                        "width": 640,
                                        "height": 100,
                                    })
                            elif network_key == "mintegral":
                                # Mintegral: app_id, placement_name, ad_type
                                ad_type_map = {
                                    "rv": "rewarded_video",
                                    "is": "new_interstitial",
                                    "bn": "banner"
                                }
                                ad_type = ad_type_map.get(slot_type.lower(), "rewarded_video")
                                unit_payload = {
                                    "app_id": "{APP_CODE}",  # Placeholder (will be replaced)
                                    "placement_name": slot_name,
                                    "ad_type": ad_type,
                                    "integrate_type": "sdk",
                                }
                                # Add type-specific fields
                                if ad_type == "rewarded_video":
                                    unit_payload["skip_time"] = -1  # Non Skippable
                                elif ad_type == "new_interstitial":
                                    unit_payload.update({
                                        "content_type": "both",
                                        "ad_space_type": 1,
                                        "skip_time": -1,
                                    })
                                elif ad_type == "banner":
                                    unit_payload.update({
                                        "show_close_button": 0,
                                        "auto_fresh": 0,
                                    })
                            elif network_key == "inmobi":
                                # InMobi: appId, placementName, placementType
                                placement_type_map = {
                                    "rv": "REWARDED_VIDEO",
                                    "is": "INTERSTITIAL",
                                    "bn": "BANNER"
                                }
                                placement_type = placement_type_map.get(slot_type.lower(), "INTERSTITIAL")
                                unit_payload = {
                                    "appId": "{APP_CODE}",  # Placeholder
                                    "placementName": slot_name,
                                    "placementType": placement_type,
                                    "isAudienceBiddingEnabled": False,
                                }
                            elif network_key == "fyber":
                                # Fyber: name, appId, placementType
                                placement_type_map = {
                                    "rv": "Rewarded",
                                    "is": "Interstitial",
                                    "bn": "Banner"
                                }
                                placement_type = placement_type_map.get(slot_type.lower(), "Rewarded")
                                unit_payload = {
                                    "name": slot_name,
                                    "appId": "{APP_CODE}",  # Placeholder
                                    "placementType": placement_type,
                                    "coppa": False,
                                }
                            elif network_key == "vungle":
                                # Vungle: name, adFormat (platform and package_name will be added separately)
                                ad_format_map = {
                                    "rv": "Rewarded",
                                    "is": "Interstitial",
                                    "bn": "Banner"
                                }
                                ad_format = ad_format_map.get(slot_type.lower(), "Rewarded")
                                unit_payload = {
                                    "name": slot_name,
                                    "adFormat": ad_format,
                                }
                            else:
                                # For other networks, try config.build_unit_payload if available
                                if hasattr(config, 'build_unit_payload'):
                                    try:
                                        # Map slot_type to network-specific format
                                        unit_payload_data = {
                                            "appCode": "{APP_CODE}",  # Placeholder (generic)
                                            "name": slot_name,
                                            "slotType": slot_type.lower()
                                        }
                                        # Try to map to network-specific field names
                                        if network_key in ["inmobi", "mintegral", "pangle"]:
                                            # These networks use different field names
                                            if network_key == "inmobi":
                                                unit_payload_data["appId"] = "{APP_CODE}"
                                            elif network_key == "mintegral":
                                                unit_payload_data["app_id"] = "{APP_CODE}"
                                            elif network_key == "pangle":
                                                unit_payload_data["site_id"] = "{APP_CODE}"
                                        
                                        unit_payload = config.build_unit_payload(unit_payload_data)
                                    except Exception as e:
                                        logger.warning(f"Failed to build unit payload for {network_key} {platform_str} {slot_type}: {str(e)}")
                                        continue
                                else:
                                    unit_payload = {
                                        "appCode": "{APP_CODE}",  # Placeholder
                                        "name": slot_name,
                                    }
                            
                            platform_unit_payloads[slot_type.upper()] = unit_payload
                    
                    if platform_unit_payloads:
                        unit_payloads[platform_key] = platform_unit_payloads
            
            preview_data[network_key] = {
                "display": network_display,
                "payloads": payloads,
                "params": mapped_params,
                "unit_payloads": unit_payloads  # Add unit payloads
            }
    
    return preview_data, has_errors
