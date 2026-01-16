"""New Create App UI - Simplified with Store URL input and network selection"""
import streamlit as st
import logging
from typing import Dict, List, Optional, Tuple
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager
from utils.ui_helpers import handle_api_response
from utils.helpers import mask_sensitive_data
from network_configs import get_network_config, get_network_display_names, NETWORK_REGISTRY
from utils.app_store_helper import get_ios_app_details, get_android_app_details

logger = logging.getLogger(__name__)


def create_ad_units_immediately(network_key: str, network_display: str, app_response: dict, mapped_params: dict, 
                                 platform: str, config, network_manager, app_name: str):
    """Create ad units immediately after app creation success
    Automatically deactivates existing ad units before creating new ones.
    
    Args:
        network_key: Network identifier (e.g., "bigoads", "inmobi")
        network_display: Network display name
        app_response: App creation response
        mapped_params: Mapped parameters from preview
        platform: Platform string ("Android" or "iOS")
        config: Network config object
        network_manager: Network manager instance
        app_name: App name
    
    Returns:
        List of created unit results
    """
    import json
    
    created_units = []
    
    # Extract app info to get appId/appCode
    app_info = extract_app_info_from_response(network_key, app_response, mapped_params)
    
    if not app_info:
        return created_units
    
    app_code = app_info.get("appCode") or app_info.get("appId") or app_info.get("appKey")
    if not app_code:
        return created_units
    
    # Step 1: Deactivate existing ad units (if needed)
    # This must be done before creating new units to avoid conflicts
    try:
        if network_key == "ironsource":
            # IronSource: Deactivate existing ad units
            from utils.ad_network_query import get_ironsource_units
            
            app_key = app_info.get("appKey") or app_code
            if app_key:
                with st.spinner(f"⏸️ {network_display} - {platform}: 기존 Ad Units 비활성화 중..."):
                    existing_units = get_ironsource_units(app_key)
                    
                    if existing_units:
                        deactivate_payloads = []
                        for unit in existing_units:
                            mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                            if mediation_adunit_id:
                                deactivate_payloads.append({
                                    "mediationAdUnitId": str(mediation_adunit_id).strip(),
                                    "isPaused": True
                                })
                        
                        if deactivate_payloads:
                            deactivate_response = network_manager._update_ironsource_ad_units(app_key, deactivate_payloads)
                            if deactivate_response.get("status") == 0:
                                st.success(f"✅ {network_display} - {platform}: {len(deactivate_payloads)}개 기존 Ad Units 비활성화 완료!")
                                logger.info(f"[{network_display}] Deactivated {len(deactivate_payloads)} existing ad units for {platform}")
                            else:
                                st.warning(f"⚠️ {network_display} - {platform}: 기존 Ad Units 비활성화 실패 (계속 진행)")
                                logger.warning(f"[{network_display}] Failed to deactivate existing ad units for {platform}: {deactivate_response.get('msg', 'Unknown error')}")
                        else:
                            logger.info(f"[{network_display}] No existing ad units to deactivate for {platform}")
                    else:
                        logger.info(f"[{network_display}] No existing ad units found for {platform}")
        
        elif network_key == "vungle":
            # Vungle: Deactivate existing placements
            vungle_app_id = app_info.get("vungleAppId") or app_code
            if vungle_app_id:
                with st.spinner(f"⏸️ {network_display} - {platform}: 기존 Placements 비활성화 중..."):
                    try:
                        existing_placements = network_manager._get_vungle_placements_by_app_id(str(vungle_app_id))
                        for placement in existing_placements:
                            initial_placement_id = placement.get("id")
                            if initial_placement_id:
                                # Get full placement details to get accurate ID
                                placement_details = network_manager._vungle_api.get_placement(str(initial_placement_id))
                                if placement_details and placement_details.get("result"):
                                    placement_id = placement_details["result"].get("id")
                                    if placement_id:
                                        # Deactivate placement
                                        deactivate_response = network_manager._vungle_api.update_placement(
                                            str(placement_id),
                                            {"isActive": False}
                                        )
                                        if deactivate_response and deactivate_response.get("code") == 0:
                                            logger.info(f"[Vungle] Deactivated placement {placement_id} for {platform}")
                        
                        if existing_placements:
                            st.success(f"✅ {network_display} - {platform}: {len(existing_placements)}개 기존 Placements 비활성화 완료!")
                    except Exception as e:
                        logger.warning(f"[Vungle] Failed to deactivate existing placements for {platform}: {str(e)}")
                        st.warning(f"⚠️ {network_display} - {platform}: 기존 Placements 비활성화 실패 (계속 진행)")
        
        elif network_key == "unity":
            # Unity: Archive existing ad units
            # Unity stores project_id and stores (apple/google) in app_info
            project_id = app_info.get("project_id") or app_info.get("projectId")
            if project_id:
                # Map platform to store_name: "iOS" -> "apple", "Android" -> "google"
                platform_lower = platform.lower()
                if platform_lower == "ios":
                    target_stores = ["apple"]
                    platform_display = "iOS"
                elif platform_lower == "android":
                    target_stores = ["google"]
                    platform_display = "Android"
                else:
                    # If platform is not specified, archive both stores
                    target_stores = ["apple", "google"]
                    platform_display = platform
                
                with st.spinner(f"📦 {network_display} - {platform_display}: 기존 Ad Units Archive 중..."):
                    try:
                        # Get existing ad units from API
                        ad_units_dict = network_manager._get_unity_ad_units(project_id)
                        
                        if ad_units_dict:
                            archived_count = 0
                            # Archive ad units for target stores only
                            for store_name in target_stores:
                                if store_name in ad_units_dict and ad_units_dict[store_name]:
                                    ad_units = ad_units_dict[store_name]
                                    
                                    # Build archive payload: {ad_unit_id: {"archive": True}}
                                    archive_payload = {}
                                    for ad_unit_id, ad_unit_data in ad_units.items():
                                        archive_payload[ad_unit_id] = {
                                            "archive": True
                                        }
                                    
                                    if archive_payload:
                                        # Archive ad units for this store
                                        archive_response = network_manager._update_unity_ad_units(project_id, store_name, archive_payload)
                                        if archive_response.get("status") == 0:
                                            archived_count += len(archive_payload)
                                            store_display = "iOS" if store_name == "apple" else "Android"
                                            logger.info(f"[Unity] Archived {len(archive_payload)} ad units for {store_display} (project_id: {project_id})")
                                        else:
                                            logger.warning(f"[Unity] Failed to archive ad units for {store_name}: {archive_response.get('msg', 'Unknown error')}")
                            
                            if archived_count > 0:
                                st.success(f"✅ {network_display} - {platform_display}: {archived_count}개 기존 Ad Units Archive 완료!")
                            else:
                                logger.info(f"[Unity] No existing ad units to archive for {platform_display} (project_id: {project_id})")
                        else:
                            logger.info(f"[Unity] No existing ad units found for project {project_id}")
                    except Exception as e:
                        logger.warning(f"[Unity] Failed to archive existing ad units for {platform_display}: {str(e)}")
                        st.warning(f"⚠️ {network_display} - {platform_display}: 기존 Ad Units Archive 실패 (계속 진행)")
    except Exception as e:
        logger.warning(f"[{network_display}] Error deactivating existing ad units for {platform}: {str(e)}")
        st.warning(f"⚠️ {network_display} - {platform}: 기존 Ad Units 비활성화 중 오류 발생 (계속 진행)")
    
    # Try to use pre-prepared unit payloads from preview_data
    preview_data = st.session_state.get("preview_data", {})
    preview_info = preview_data.get(network_key, {})
    unit_payloads = preview_info.get("unit_payloads", {})
    
    # Determine platform key for unit payloads
    platform_key = platform if platform in unit_payloads else ("default" if "default" in unit_payloads else None)
    
    if platform_key and platform_key in unit_payloads:
        # Use pre-prepared unit payloads
        platform_units = unit_payloads[platform_key]
        
        for slot_type, unit_payload_template in platform_units.items():
            try:
                # Deep copy the template payload
                unit_payload = json.loads(json.dumps(unit_payload_template))
                
                # Replace {APP_CODE} placeholder with actual app_code
                def replace_app_code(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, str) and "{APP_CODE}" in value:
                                replaced_value = value.replace("{APP_CODE}", str(app_code).strip())
                                # For Mintegral, convert app_id to integer
                                if network_key == "mintegral" and key == "app_id":
                                    try:
                                        obj[key] = int(replaced_value)
                                    except (ValueError, TypeError):
                                        obj[key] = replaced_value
                                else:
                                    obj[key] = replaced_value
                            elif isinstance(value, (dict, list)):
                                replace_app_code(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            replace_app_code(item)
                
                replace_app_code(unit_payload)
                
                # Create unit
                with st.spinner(f"{network_display} - {platform} {slot_type} Unit 생성 중..."):
                    unit_response = network_manager.create_unit(network_key, unit_payload)
                    
                    unit_success = unit_response.get('status') == 0 or unit_response.get('code') == 0
                    if unit_success:
                        st.success(f"✅ {network_display} - {platform} {slot_type} Unit 생성 완료!")
                        if network_key not in st.session_state.creation_results:
                            st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                        unit_name = unit_payload.get("name", f"{slot_type}_unit")
                        st.session_state.creation_results[network_key]["units"].append({
                            "platform": platform,
                            "app_name": app_name,
                            "unit_name": unit_name,
                            "unit_type": slot_type,
                            "success": True
                        })
                        created_units.append({"slot_type": slot_type, "success": True, "slot_name": unit_name})
                    else:
                        error_msg = unit_response.get("msg", "Unknown error") if unit_response else "No response"
                        st.warning(f"⚠️ {network_display} - {platform} {slot_type} Unit 생성 실패: {error_msg}")
                        created_units.append({"slot_type": slot_type, "success": False, "error": error_msg})
            except Exception as e:
                st.warning(f"⚠️ {network_display} - {platform} {slot_type} Unit 생성 실패: {str(e)}")
                logger.error(f"Error creating {slot_type} unit for {network_key} {platform}: {str(e)}", exc_info=True)
                created_units.append({"slot_type": slot_type, "success": False, "error": str(e)})
    else:
        # Fallback to original logic if pre-prepared payloads not available
        from components.create_app_helpers import generate_slot_name
        
        # Get package name/bundle ID for unit name generation
        platform_lower = platform.lower()
        if platform_lower == "android":
            pkg_name = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("androidBundle", ""))))
            if not pkg_name and network_key == "inmobi":
                android_info = st.session_state.get("store_info_android", {})
                if android_info:
                    pkg_name = android_info.get("package_name", "")
            bundle_id = ""
            android_package_for_unit = None
        else:  # iOS
            pkg_name = ""
            bundle_id = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("iosBundle", ""))))
            if not bundle_id and network_key == "inmobi":
                ios_info = st.session_state.get("store_info_ios", {})
                if ios_info:
                    bundle_id = ios_info.get("bundle_id", "")
            
            # For iOS, use user-selected identifier if available, otherwise try Android package name
            android_package_for_unit = None
            if "ios_ad_unit_identifier" in st.session_state:
                # Use user-selected value
                selected_identifier = st.session_state.ios_ad_unit_identifier.get("value", "")
                if selected_identifier:
                    android_package_for_unit = selected_identifier
            else:
                # Fallback: try to use Android package name if available
                android_package_for_unit = mapped_params.get("android_package", mapped_params.get("androidPkgName", ""))
                if not android_package_for_unit and network_key == "inmobi":
                    android_info = st.session_state.get("store_info_android", {})
                    if android_info:
                        android_package_for_unit = android_info.get("package_name", "")
                        # Extract last part if it's a full package name
                        if '.' in android_package_for_unit:
                            android_package_for_unit = android_package_for_unit.split('.')[-1]
        
        # Create RV, IS, BN units sequentially
        for slot_type in ["rv", "is", "bn"]:
            slot_name = generate_slot_name(
                pkg_name,
                platform_lower,
                slot_type,
                network_key,
                bundle_id=bundle_id,
                network_manager=network_manager,
                app_name=app_name,
                android_package_name=android_package_for_unit if platform_lower == "ios" else None
            )
            
            if slot_name:
                try:
                    # Build unit payload
                    if network_key == "bigoads":
                        unit_payload = {
                            "appCode": str(app_code).strip(),
                            "name": slot_name,
                        }
                        if slot_type.lower() == "rv":
                            unit_payload.update({"adType": 4, "auctionType": 3, "musicSwitch": 1})
                        elif slot_type.lower() == "is":
                            unit_payload.update({"adType": 3, "auctionType": 3, "musicSwitch": 1})
                        elif slot_type.lower() == "bn":
                            unit_payload.update({"adType": 2, "auctionType": 3, "bannerAutoRefresh": 2, "bannerSize": [2]})
                    else:
                        # Use config.build_unit_payload if available
                        if hasattr(config, 'build_unit_payload'):
                            unit_payload = config.build_unit_payload({
                                "appCode": str(app_code).strip(),
                                "name": slot_name,
                                "slotType": slot_type.lower()
                            })
                        else:
                            unit_payload = {
                                "appCode": str(app_code).strip(),
                                "name": slot_name,
                            }
                    
                    # Create unit
                    with st.spinner(f"{network_display} - {platform} {slot_type.upper()} Unit 생성 중..."):
                        unit_response = network_manager.create_unit(network_key, unit_payload)
                        
                        unit_success = unit_response.get('status') == 0 or unit_response.get('code') == 0
                        if unit_success:
                            st.success(f"✅ {network_display} - {platform} {slot_type.upper()} Unit 생성 완료!")
                            if network_key not in st.session_state.creation_results:
                                st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                            st.session_state.creation_results[network_key]["units"].append({
                                "platform": platform,
                                "app_name": app_name,
                                "unit_name": slot_name,
                                "unit_type": slot_type.upper(),
                                "success": True
                            })
                            created_units.append({"slot_type": slot_type.upper(), "success": True, "slot_name": slot_name})
                        else:
                            error_msg = unit_response.get("msg", "Unknown error") if unit_response else "No response"
                            st.warning(f"⚠️ {network_display} - {platform} {slot_type.upper()} Unit 생성 실패: {error_msg}")
                            created_units.append({"slot_type": slot_type.upper(), "success": False, "error": error_msg})
                except Exception as e:
                    st.warning(f"⚠️ {network_display} - {platform} {slot_type.upper()} Unit 생성 실패: {str(e)}")
                    logger.error(f"Error creating {slot_type} unit for {network_key} {platform}: {str(e)}", exc_info=True)
                    created_units.append({"slot_type": slot_type.upper(), "success": False, "error": str(e)})
    
    return created_units


def extract_app_info_from_response(network_key, response, mapped_params):
    """Extract app info (appId, appCode, gameId, etc.) from create app response"""
    if not response or not isinstance(response, dict):
        return None
    
    result = response.get('result', {})
    if not result:
        result = response
    
    app_info = {}
    
    # Network-specific extraction
    if network_key == "ironsource":
        # IronSource: appKey from result
        app_info["appKey"] = result.get("appKey") or response.get("appKey")
        app_info["appCode"] = app_info["appKey"]
    elif network_key == "mintegral":
        # Mintegral: app_id from result.result
        app_id = result.get("app_id") or result.get("id") or result.get("appId")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "inmobi":
        # InMobi: appId from result.data or result
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
        app_id = data.get("appId") or data.get("id") or result.get("appId")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "bigoads":
        # BigOAds: appCode from result.result
        app_code = result.get("appCode") or response.get("appCode")
        app_info["appCode"] = app_code
    elif network_key == "fyber":
        # Fyber: appId from result.result
        app_id = result.get("appId") or result.get("id")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "unity":
        # Unity: gameId from result.result.stores
        stores = result.get("stores", {})
        apple_store = stores.get("apple", {}) if isinstance(stores.get("apple"), dict) else {}
        google_store = stores.get("google", {}) if isinstance(stores.get("google"), dict) else {}
        apple_game_id = apple_store.get("gameId")
        google_game_id = google_store.get("gameId")
        project_id = result.get("id")
        app_info["apple_gameId"] = apple_game_id
        app_info["google_gameId"] = google_game_id
        app_info["project_id"] = project_id
        app_info["appCode"] = str(apple_game_id) if apple_game_id else (str(google_game_id) if google_game_id else str(project_id) if project_id else None)
    elif network_key == "pangle":
        # Pangle: app_id from result.result (normalized response structure)
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
        app_id = result_data.get("app_id")
        app_info["appId"] = app_id
        app_info["siteId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "vungle":
        # Vungle: vungleAppId from result (response is the app object itself)
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        vungle_app_id = result_data.get("vungleAppId") or result_data.get("id")
        app_info["vungleAppId"] = vungle_app_id
        app_info["appId"] = vungle_app_id
        app_info["appCode"] = str(vungle_app_id) if vungle_app_id else None
        app_info["platform"] = result_data.get("platform", "")  # "ios" or "android"
        app_info["name"] = result_data.get("name", "")
        
        # Extract platform-specific package name/bundle ID from mapped_params
        platform_value = result_data.get("platform", "").lower()
        if platform_value == "android":
            app_info["pkgName"] = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
            app_info["platformStr"] = "android"
        elif platform_value == "ios":
            app_info["bundleId"] = mapped_params.get("ios_store_id", mapped_params.get("iosAppId", ""))
            app_info["pkgName"] = ""  # iOS doesn't use pkgName
            app_info["platformStr"] = "ios"
    else:
        # Default: try common fields
        app_code = result.get("appCode") or result.get("appId") or result.get("appKey") or result.get("id")
        app_info["appCode"] = app_code
    
    # Add common fields
    app_info["name"] = result.get("name") or mapped_params.get("name") or mapped_params.get("app_name") or "Unknown"
    
    # Extract platform-specific package name and bundle ID for all networks
    # Android: use package name, iOS: use bundle ID
    platform_str = mapped_params.get("platformStr") or mapped_params.get("platform", "android")
    platform_value = platform_str.lower() if isinstance(platform_str, str) else "android"
    
    # For multi-platform networks, extract from platform-specific fields in mapped_params
    if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "mintegral", "pangle"]:
        # Try to get from platform-specific fields first
        if platform_value == "android" or "Android" in str(platform_str):
            app_info["pkgName"] = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("package", ""))))
            app_info["bundleId"] = ""  # Android doesn't use bundleId
            app_info["platformStr"] = "android"
        elif platform_value == "ios" or "iOS" in str(platform_str) or "IOS" in str(platform_str):
            app_info["pkgName"] = ""  # iOS doesn't use pkgName
            app_info["bundleId"] = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("bundle", mapped_params.get("bundleId", "")))))
            app_info["platformStr"] = "ios"
        else:
            # Fallback: try generic fields
            app_info["pkgName"] = mapped_params.get("pkgName") or mapped_params.get("package", "")
            app_info["bundleId"] = mapped_params.get("bundleId") or mapped_params.get("bundle", "")
            app_info["platformStr"] = platform_value
    else:
        # Single platform or other networks: use generic fields
        app_info["pkgName"] = mapped_params.get("pkgName") or mapped_params.get("package", "")
        app_info["bundleId"] = mapped_params.get("bundleId") or mapped_params.get("bundle", "")
        app_info["platformStr"] = platform_value
    
    return app_info if app_info.get("appCode") else None


def map_store_info_to_network_params(
    ios_info: Optional[Dict],
    android_info: Optional[Dict],
    network: str,
    config
) -> Dict:
    """Map App Store info to network-specific parameters
    
    Args:
        ios_info: iOS app details from App Store
        android_info: Android app details from Play Store
        network: Network identifier
        config: Network configuration object
    
    Returns:
        Dictionary with network-specific parameters filled in
    """
    params = {}
    
    # Common fields that most networks use
    app_name = None
    if ios_info:
        app_name = ios_info.get("name")
    if not app_name and android_info:
        app_name = android_info.get("name")
    
    # Network-specific mapping
    if network == "ironsource":
        params["appName"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        
        # Use taxonomy from session state (user-selected or auto-matched)
        # If not in session state, try to match from App Store category
        if "ironsource_taxonomy" in st.session_state:
            params["taxonomy"] = st.session_state.ironsource_taxonomy
        else:
            # Map App Store category to IronSource taxonomy
            from components.one_click.category_matchers import match_ironsource_taxonomy
            
            # Get category from Android first (priority), then iOS
            android_category = None
            ios_category = None
            if android_info:
                android_category = android_info.get("category", "")
            if ios_info:
                ios_category = ios_info.get("category", "")
            
            # Use Android category if available (priority)
            app_category = android_category if android_category else ios_category
            
            # Get taxonomy options from config
            taxonomy_options = config._get_taxonomies() if hasattr(config, '_get_taxonomies') else []
            
            # Match category to taxonomy (pass Android category for better matching)
            matched_taxonomy = match_ironsource_taxonomy(
                app_category, 
                taxonomy_options,
                android_category=android_category if android_category else None
            ) if app_category else "other"
            params["taxonomy"] = matched_taxonomy
            # Store in session state for future use
            st.session_state.ironsource_taxonomy = matched_taxonomy
        
        params["coppa"] = 0  # Default: Not child-directed
    
    elif network == "inmobi":
        params["appName"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Default values
        params["childDirected"] = 2  # Not child-directed
        params["locationAccess"] = True
    
    elif network == "bigoads":
        params["name"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
            params["iosPkgName"] = ios_info.get("bundle_id", "")
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
            params["androidPkgName"] = android_info.get("package_name", "")
        # Default values (from BigOAdsConfig defaults)
        params["mediaType"] = 1  # Always Application (1)
        params["mediationPlatform"] = [1]  # Default: MAX
        params["category"] = "GAME_CASUAL"  # Default category
        params["coppaOption"] = 1  # Default: Not child-directed
        params["screenDirection"] = 0  # Default: Vertical
    
    elif network == "fyber":
        params["name"] = app_name or ""
        
        # Import category matchers
        from components.one_click.category_matchers import match_fyber_android_category, match_fyber_ios_category
        
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
            params["iosBundle"] = ios_info.get("bundle_id", "")
            # Map iOS category from App Store to Fyber iOS category
            ios_category = ios_info.get("category", "")
            android_category = android_info.get("category", "") if android_info else ""
            fyber_ios_categories = config._get_categories("ios")
            matched_ios_category = match_fyber_ios_category(ios_category, android_category, fyber_ios_categories)
            params["iosCategory1"] = matched_ios_category or "Games"  # Default to "Games" if no match
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
            params["androidBundle"] = android_info.get("package_name", "")
            # Map Android category from Play Store to Fyber Android category
            android_category = android_info.get("category", "")
            fyber_android_categories = config._get_categories("android")
            matched_android_category = match_fyber_android_category(android_category, fyber_android_categories)
            params["androidCategory1"] = matched_android_category or "Games - Casual"  # Default to "Games - Casual" if no match
        params["coppa"] = "false"  # Default: Not child-directed
    
    elif network == "pangle":
        # Pangle uses platform-specific app names
        # Store both platform app names and URLs for multi-platform support
        if ios_info:
            params["iosAppName"] = ios_info.get("name", "")
            params["iosDownloadUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidAppName"] = android_info.get("name", "")
            params["androidDownloadUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Fallback to common app_name if platform-specific names not available
        params["app_name"] = app_name or ""
        # Note: user_id and role_id are NOT included in params
        # They will be added by pangle_api.py from environment variables
        # This ensures consistency and prevents params from overriding .env values
        # Match app_category_code from iOS and Android categories
        ios_category = ios_info.get("category", "") if ios_info else None
        android_category = android_info.get("category", "") if android_info else None
        params["app_category_code"] = config.match_category_code(ios_category, android_category)
        params["coppa_value"] = 0  # Default: For users aged 13 and above
        params["mask_rule_ids"] = "531582"  # Default mask rule IDs
    
    elif network == "mintegral":
        # Mintegral requires separate payloads for iOS and Android
        # Store base params separately for each platform
        params["app_name"] = app_name or ""
        # Note: os, package, store_url will be set per platform in build_app_payload
        # Default values (common for both platforms)
        params["appType"] = 1  # Application
        params["category"] = "Games"
        params["is_live_in_store"] = 1  # Default: Live in store (requires store_url)
        params["coppa"] = 0  # Default: Not child-directed
        
        # Store platform-specific info separately
        if ios_info:
            params["ios_itunesId"] = ios_info.get("app_id", "")
            params["ios_package"] = ios_info.get("bundle_id", "")
            params["ios_store_url"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["android_package"] = android_info.get("package_name", "")
            params["android_store_url"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
    
    elif network == "unity":
        params["name"] = app_name or ""
        if ios_info:
            params["apple_storeId"] = ios_info.get("app_id", "")
            params["apple_storeUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["google_storeId"] = android_info.get("package_name", "")
            params["google_storeUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Default values
        params["adsProvider"] = ["max"]  # Default: MAX
        params["coppa"] = "non_compliant"  # Default
    
    elif network == "vungle":
        # Vungle requires separate payloads for iOS and Android
        # Store base params separately for each platform
        params["name"] = app_name or ""
        
        # Store platform-specific info separately
        if ios_info:
            params["ios_name"] = ios_info.get("name", "")
            params["ios_store_id"] = ios_info.get("app_id", "")  # App ID for iOS
            params["ios_store_url"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["android_name"] = android_info.get("name", "")
            params["android_store_id"] = android_info.get("package_name", "")  # Package name for Android
            params["android_store_url"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
    
    return params


def render_new_create_app_ui():
    """Render the new simplified Create App UI"""
    st.subheader("📱 Create App (New)")
    
    # Step 1: Store URL Input
    st.markdown("### 1️⃣ Store URL 입력")
    col_android, col_ios = st.columns(2)
    
    with col_android:
        android_url = st.text_input(
            "🤖 Google Play Store URL",
            placeholder="https://play.google.com/store/apps/details?id=...",
            key="new_android_url",
            help="Android 앱의 Google Play Store URL을 입력하세요"
        )
    
    with col_ios:
        ios_url = st.text_input(
            "🍎 App Store URL",
            placeholder="https://apps.apple.com/us/app/...",
            key="new_ios_url",
            help="iOS 앱의 App Store URL을 입력하세요"
        )
    
    # Fetch button
    fetch_info_button = st.button("🔍 앱 정보 조회", type="primary", width='stretch')
    
    # Initialize session state
    if "store_info_ios" not in st.session_state:
        st.session_state.store_info_ios = None
    if "store_info_android" not in st.session_state:
        st.session_state.store_info_android = None
    if "selected_networks" not in st.session_state:
        st.session_state.selected_networks = []
    
    # Fetch app store info
    if fetch_info_button:
        ios_info = None
        android_info = None
        
        if ios_url:
            with st.spinner("iOS 앱 정보를 가져오는 중..."):
                try:
                    ios_info = get_ios_app_details(ios_url)
                    if ios_info:
                        st.session_state.store_info_ios = ios_info
                        st.success(f"✅ iOS 앱 정보 조회 성공: {ios_info.get('name', 'N/A')}")
                    else:
                        st.error("❌ iOS 앱 정보를 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ iOS 앱 정보 조회 실패: {str(e)}")
        
        if android_url:
            with st.spinner("Android 앱 정보를 가져오는 중..."):
                try:
                    android_info = get_android_app_details(android_url)
                    if android_info:
                        st.session_state.store_info_android = android_info
                        st.success(f"✅ Android 앱 정보 조회 성공: {android_info.get('name', 'N/A')}")
                    else:
                        st.error("❌ Android 앱 정보를 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ Android 앱 정보 조회 실패: {str(e)}")
        
        if not ios_url and not android_url:
            st.warning("⚠️ 최소 하나의 Store URL을 입력해주세요.")
    
    # Display fetched info
    if st.session_state.store_info_ios or st.session_state.store_info_android:
        st.markdown("### 📋 조회된 앱 정보")
        
        info_cols = st.columns(2)
        
        with info_cols[0]:
            if st.session_state.store_info_android:
                info = st.session_state.store_info_android
                st.markdown("**🤖 Android**")
                st.write(f"**이름:** {info.get('name', 'N/A')}")
                st.write(f"**Package Name:** {info.get('package_name', 'N/A')}")
                st.write(f"**개발자:** {info.get('developer', 'N/A')}")
                st.write(f"**카테고리:** {info.get('category', 'N/A')}")
        
        with info_cols[1]:
            if st.session_state.store_info_ios:
                info = st.session_state.store_info_ios
                st.markdown("**🍎 iOS**")
                st.write(f"**이름:** {info.get('name', 'N/A')}")
                st.write(f"**Bundle ID:** {info.get('bundle_id', 'N/A')}")
                st.write(f"**App ID:** {info.get('app_id', 'N/A')}")
                st.write(f"**개발자:** {info.get('developer', 'N/A')}")
                st.write(f"**카테고리:** {info.get('category', 'N/A')}")
        
        # Check if Android Package Name and iOS Bundle ID are different
        android_package = None
        ios_bundle_id = None
        
        if st.session_state.store_info_android:
            android_package = st.session_state.store_info_android.get('package_name', '')
        if st.session_state.store_info_ios:
            ios_bundle_id = st.session_state.store_info_ios.get('bundle_id', '')
        
        # Layout: 좌우 배치 (Ad Unit 식별자 선택 | IronSource Taxonomy 선택)
        st.divider()
        left_col, right_col = st.columns(2)
        
        # Left column: Ad Unit 이름 생성용 식별자 선택
        with left_col:
            # Show button to open dialog if both exist and are different
            if android_package and ios_bundle_id and android_package != ios_bundle_id:
                st.markdown("### 🔀 App match name")
                
                # Initialize selection in session state if not exists
                if "ios_ad_unit_identifier" not in st.session_state:
                    # Default: use Android Package Name (last part), convert to lowercase
                    android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
                    st.session_state.ios_ad_unit_identifier = {
                        "source": "android_package",
                        "value": android_package_last.lower()
                    }
                
                # Show current selection status
                selected_value = st.session_state.ios_ad_unit_identifier.get("value", "")
                if selected_value:
                    st.info(f"**선택된 값:** `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
                
                # Define dialog function
                @st.dialog("🔀 App match name 선택")
                def identifier_selection_dialog():
                    st.markdown("### 🔀 App match name")
                    st.info("💡 Android Package Name과 iOS Bundle ID가 다릅니다. Ad Unit 이름 생성 시 어떤 값을 사용할지 선택하거나 직접 입력하세요.")
                    
                    # Extract last part of Android Package Name
                    android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
                    ios_bundle_id_last = ios_bundle_id.split('.')[-1] if '.' in ios_bundle_id else ios_bundle_id
                    
                    # Selection options (display original case, but store lowercase)
                    selection_options = [
                        f"Android Package Name: `{android_package_last}`",
                        f"iOS Bundle ID: `{ios_bundle_id_last}`",
                        "직접 입력"
                    ]
                    
                    # Get current selection
                    current_selection = st.session_state.ios_ad_unit_identifier.get("source", "android_package")
                    if current_selection == "android_package":
                        current_index = 0
                    elif current_selection == "ios_bundle_id":
                        current_index = 1
                    else:
                        current_index = 2
                    
                    selected_option = st.radio(
                        "선택하세요:",
                        options=selection_options,
                        index=current_index,
                        key="ios_ad_unit_identifier_radio_dialog"
                    )
                    
                    # Update session state based on selection (convert to lowercase)
                    if selected_option.startswith("Android Package Name"):
                        st.session_state.ios_ad_unit_identifier = {
                            "source": "android_package",
                            "value": android_package_last.lower()
                        }
                    elif selected_option.startswith("iOS Bundle ID"):
                        st.session_state.ios_ad_unit_identifier = {
                            "source": "ios_bundle_id",
                            "value": ios_bundle_id_last.lower()
                        }
                    else:  # 직접 입력
                        custom_value = st.text_input(
                            "직접 입력:",
                            value=st.session_state.ios_ad_unit_identifier.get("value", ""),
                            key="ios_ad_unit_identifier_custom_dialog",
                            help="Ad Unit 이름 생성에 사용할 식별자를 직접 입력하세요 (소문자로 저장됩니다)"
                        )
                        if custom_value:
                            st.session_state.ios_ad_unit_identifier = {
                                "source": "custom",
                                "value": custom_value.lower()
                            }
                    
                    # Show preview
                    selected_value = st.session_state.ios_ad_unit_identifier.get("value", "")
                    if selected_value:
                        st.success(f"✅ 선택된 값: `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
                    
                    # Close dialog buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 확인", key="confirm_identifier_dialog", width='stretch', type="primary"):
                            st.rerun()
                    with col2:
                        if st.button("❌ 취소", key="cancel_identifier_dialog", width='stretch'):
                            st.rerun()
                
                # Button to open dialog
                if st.button("🔀 App match name 선택", key="open_identifier_dialog", width='stretch'):
                    identifier_selection_dialog()
            else:
                st.markdown("### 🔀 App match name")
                st.info("💡 Android Package Name과 iOS Bundle ID가 같거나 하나만 입력된 경우 이 기능을 사용할 수 없습니다.")
        
        # Right column: IronSource Taxonomy Selection
        with right_col:
            st.markdown("### 📂 IronSource Taxonomy")
            st.info("💡 IronSource 네트워크를 사용하는 경우, Taxonomy (Sub-genre)를 선택해주세요. 카테고리가 자동으로 매칭되지만 수동으로 변경할 수 있습니다.")
            
            # Initialize taxonomy in session state if not exists
            if "ironsource_taxonomy" not in st.session_state:
                st.session_state.ironsource_taxonomy = "other"
            
            # Get taxonomy options
            from network_configs.ironsource_config import IronSourceConfig
            ironsource_config = IronSourceConfig()
            taxonomy_options = ironsource_config._get_taxonomies()
            
            # Build hierarchical taxonomy structure from images
            taxonomy_structure = {
                "Casual": {
                    "Hyper Casual": ["stacking", "dexterity", "rising/falling", "swerve", "merge", "idle", ".io", "puzzle", "tap/Timing", "turning", "ball", "other"],
                    "Puzzle": ["actionPuzzle", "match3", "bubbleShooter", "jigsaw", "crossword", "word", "trivia", "board", "coloring Games", "hidden Objects", "solitaire", "nonCasinoCardGame", "otherPuzzle"],
                    "Arcade": ["platformer", "idler", "shootEmUp", "endlessRunner", "towerDefense", "otherArcade"],
                    "Lifestyle": ["customization", "interactiveStory", "music/band", "otherLifestyle"],
                    "Simulation": ["adventures", "breeding", "tycoon/crafting", "sandbox", "cooking/timeManagement", "farming", "idleSimulation", "otherSimulation"],
                    "Kids & Family": ["kids&Family"],
                    "Other Casual": ["otherCasual"]
                },
                "Mid-Core": {
                    "Shooter": ["battleRoyale", "classicFPS", "snipers", "tacticalShooter", "otherShooter"],
                    "RPG": ["actionRPG", "turnBasedRPG", "fighting", "MMORPG", "puzzleRPG", "survival", "idleRPG", "otherRPG"],
                    "Card Games": ["cardBattler"],
                    "Strategy": ["4xStrategy", "build&Battle", "MOBA", "syncBattler", "otherStrategy"],
                    "Other Mid-Core": ["otherMidCore"]
                },
                "Sports & Racing": {
                    "Sports": ["casualSports", "licensedSports"],
                    "Racing": ["casualRacing", "simulationRacing", "otherRacing"],
                    "Other Sports & Racing": ["otherSports&Racing"]
                }
            }
            
            # Create API value to display name mapping
            api_to_display = {api_value: display_name for display_name, api_value in taxonomy_options}
            
            # Auto-match taxonomy from app category (if not already set)
            # Priority: Android category first, then iOS category
            if st.session_state.ironsource_taxonomy == "other":
                android_category = None
                ios_category = None
                
                if st.session_state.store_info_android:
                    android_category = st.session_state.store_info_android.get("category", "")
                if st.session_state.store_info_ios:
                    ios_category = st.session_state.store_info_ios.get("category", "")
                
                # Try Android category first (priority)
                app_category = android_category if android_category else ios_category
                
                if app_category:
                    from components.one_click.category_matchers import match_ironsource_taxonomy
                    # Pass Android category for better matching (if available)
                    auto_matched_taxonomy = match_ironsource_taxonomy(
                        app_category, 
                        taxonomy_options,
                        android_category=android_category if android_category else None
                    )
                    if auto_matched_taxonomy and auto_matched_taxonomy != "other":
                        st.session_state.ironsource_taxonomy = auto_matched_taxonomy
                        if auto_matched_taxonomy in api_to_display:
                            category_source = "Android" if android_category else "iOS"
                            st.success(f"💡 자동 매칭 ({category_source}): '{app_category}' → '{api_to_display[auto_matched_taxonomy]}'")
            
            # Build flat list of all taxonomy options with category/genre info for display
            taxonomy_display_options = []
            for category, genres in taxonomy_structure.items():
                for genre, sub_genres in genres.items():
                    for sub_genre in sub_genres:
                        display_name = api_to_display.get(sub_genre, sub_genre)
                        taxonomy_display_options.append((f"{category} > {genre} > {display_name}", sub_genre))
            
            # Create selectbox with hierarchical display
            selected_index = 0
            for idx, (display_name, api_value) in enumerate(taxonomy_display_options):
                if api_value == st.session_state.ironsource_taxonomy:
                    selected_index = idx
                    break
            
            selected_taxonomy_display = st.selectbox(
                "Taxonomy (Sub-genre)*",
                options=[opt[0] for opt in taxonomy_display_options],
                index=selected_index,
                key="ironsource_taxonomy_select",
                help="IronSource Taxonomy를 선택하세요. 계층 구조: Category > Genre > Sub-genre"
            )
            
            # Extract API value from selected display
            for display_name, api_value in taxonomy_display_options:
                if display_name == selected_taxonomy_display:
                    st.session_state.ironsource_taxonomy = api_value
                    break
        
        st.divider()
        
        # Step 2: Network Selection
        st.markdown("### 2️⃣ 네트워크 선택")
        st.markdown("앱을 생성할 네트워크를 선택하세요 (여러 개 선택 가능)")
        
        # Get available networks (include AppLovin even though it doesn't support create app)
        available_networks = {}
        display_names = get_network_display_names()
        
        # Collect all networks (including AppLovin for Ad Unit creation only)
        all_networks = {}
        for network_key, network_config in NETWORK_REGISTRY.items():
            # Include AppLovin even if it doesn't support create app (for Ad Unit creation)
            if network_config.supports_create_app() or network_key == "applovin":
                all_networks[network_key] = display_names.get(network_key, network_key.title())
        
        # Sort networks: AppLovin, Unity, IronSource, then alphabetical, Pangle last
        priority_networks = ["applovin", "unity", "ironsource"]
        sorted_networks = []
        
        # Add priority networks first
        for priority_key in priority_networks:
            if priority_key in all_networks:
                sorted_networks.append((priority_key, all_networks[priority_key]))
        
        # Add remaining networks in alphabetical order (excluding priority)
        remaining_networks = []
        for network_key, network_display in all_networks.items():
            if network_key not in priority_networks:
                remaining_networks.append((network_key, network_display))
        
        # Sort remaining networks alphabetically by display name
        remaining_networks.sort(key=lambda x: x[1])
        sorted_networks.extend(remaining_networks)
        
        # Convert to ordered dict
        available_networks = dict(sorted_networks)
        
        # Select All / Deselect All buttons
        button_cols = st.columns([1, 1, 4])
        with button_cols[0]:
            if st.button("✅ 모두 선택", key="select_all_networks", width='stretch'):
                # Select all networks
                enabled_networks = list(available_networks.keys())
                st.session_state.selected_networks = enabled_networks
                # Update individual checkbox states
                for network_key in enabled_networks:
                    st.session_state[f"network_checkbox_{network_key}"] = True
                st.rerun()
        
        with button_cols[1]:
            if st.button("❌ 선택 해제", key="deselect_all_networks", width='stretch'):
                st.session_state.selected_networks = []
                # Update individual checkbox states
                for network_key in available_networks.keys():
                    st.session_state[f"network_checkbox_{network_key}"] = False
                st.rerun()
        
        # Network selection with checkboxes
        selected_networks = []
        network_cols = st.columns(3)
        
        for idx, (network_key, network_display) in enumerate(available_networks.items()):
            with network_cols[idx % 3]:
                # No disabled networks
                is_disabled = False
                display_label = network_display
                help_text = None
                
                # Initialize checkbox state if not exists
                checkbox_key = f"network_checkbox_{network_key}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = network_key in st.session_state.selected_networks
                
                # Get checkbox value from session state
                checkbox_value = st.session_state[checkbox_key]
                
                # Create checkbox (will update session state automatically)
                is_checked = st.checkbox(
                    display_label,
                    key=checkbox_key,
                    value=checkbox_value,
                    help=help_text
                )

                # Update selected_networks list based on checkbox state
                if is_checked:
                    if network_key not in selected_networks:
                        selected_networks.append(network_key)
                elif network_key in selected_networks:
                        # If unchecked, remove from selected_networks
                            selected_networks.remove(network_key)
        
        st.session_state.selected_networks = selected_networks
        
        if not selected_networks:
            st.info("💡 네트워크를 선택해주세요.")
        else:
            st.success(f"✅ {len(selected_networks)}개 네트워크 선택됨: {', '.join([available_networks[n] for n in selected_networks])}")
            
            st.divider()
            
            # Step 3: Preview Payloads (before creating)
            st.markdown("### 3️⃣ Payload 미리보기")
            st.markdown("각 네트워크별로 전송될 API Payload를 확인하세요.")
            
            # Generate and show payload previews for all selected networks
            # Store in session state so it's available after button click
            if "preview_data" not in st.session_state:
                st.session_state.preview_data = {}
            
            # Clear BigOAds apps cache at the start of preview generation
            # This ensures we fetch fresh data once per preview generation and reuse it
            from components import create_app_helpers
            create_app_helpers._bigoads_apps_cache = None
            
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
                    st.session_state.store_info_ios,
                    st.session_state.store_info_android,
                    network_key,
                    config
                )
                
                # Build payloads for preview (check required fields during payload building)
                payloads = {}
                
                # Handle networks that support both iOS and Android
                if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "pangle", "vungle"]:
                    if st.session_state.store_info_android:
                        try:
                            android_payload = config.build_app_payload(mapped_params, platform="Android")
                            payloads["Android"] = android_payload
                        except Exception as e:
                            payloads["Android"] = {"error": str(e)}
                            has_errors = True
                    
                    if st.session_state.store_info_ios:
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
                    
                    if st.session_state.store_info_android:
                        # Check Android required fields
                        android_params = mapped_params.copy()
                        android_params["os"] = "ANDROID"
                        android_params["package"] = mapped_params.get("android_package", "")
                        android_params["store_url"] = mapped_params.get("android_store_url", "")
                        
                        required_fields = config.get_app_creation_fields()
                        for field in required_fields:
                            if field.required and field.name not in android_params:
                                from network_configs.base_config import ConditionalField
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
                    
                    if st.session_state.store_info_ios:
                        # Check iOS required fields
                        ios_params = mapped_params.copy()
                        ios_params["os"] = "IOS"
                        ios_params["package"] = mapped_params.get("ios_package", "")
                        ios_params["store_url"] = mapped_params.get("ios_store_url", "")
                        
                        required_fields = config.get_app_creation_fields()
                        for field in required_fields:
                            if field.required and field.name not in ios_params:
                                from network_configs.base_config import ConditionalField
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
                            from network_configs.base_config import ConditionalField
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
                        from components.create_app_helpers import generate_slot_name
                        network_manager = get_network_manager()
                        
                        # Get app name
                        app_name = None
                        if st.session_state.store_info_ios:
                            app_name = st.session_state.store_info_ios.get("name", "")
                        if not app_name and st.session_state.store_info_android:
                            app_name = st.session_state.store_info_android.get("name", "")
                        
                        # Generate unit payloads for each platform
                        for platform_key, platform_payload in payloads.items():
                            if "error" in platform_payload:
                                continue
                            
                            platform_str = platform_key if platform_key != "default" else "Android"
                            platform_lower = platform_str.lower()
                            
                            # Get package name/bundle ID for unit name generation
                            # Use user-selected App match name for both Android and iOS if available
                            selected_app_match_name = None
                            if "ios_ad_unit_identifier" in st.session_state:
                                selected_app_match_name = st.session_state.ios_ad_unit_identifier.get("value", None)
                            
                            if platform_lower == "android":
                                # For Android, use selected App match name if available, otherwise use package name
                                if selected_app_match_name:
                                    # Use selected App match name (already lowercase)
                                    pkg_name = selected_app_match_name
                                    bundle_id = ""
                                else:
                                    # Fallback to package name
                                    pkg_name = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("androidBundle", ""))))
                                    if not pkg_name and network_key == "inmobi":
                                        android_info = st.session_state.get("store_info_android", {})
                                        if android_info:
                                            pkg_name = android_info.get("package_name", "")
                                    bundle_id = ""
                                
                                # Always use selected App match name for unit name generation (for consistency)
                                android_package_for_unit = selected_app_match_name
                            else:  # iOS
                                pkg_name = ""
                                # For Vungle iOS, avoid using iTunesId (ios_store_id might be iTunesId)
                                # Use bundle_id directly from store_info_ios
                                if network_key == "vungle":
                                    ios_info = st.session_state.get("store_info_ios", {})
                                    if ios_info:
                                        bundle_id = ios_info.get("bundle_id", "")  # Use bundle_id, not iTunesId
                                    else:
                                        bundle_id = mapped_params.get("ios_bundle_id", mapped_params.get("iosBundle", ""))
                                else:
                                    bundle_id = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("iosBundle", ""))))
                                    if not bundle_id and network_key == "inmobi":
                                        ios_info = st.session_state.get("store_info_ios", {})
                                        if ios_info:
                                            bundle_id = ios_info.get("bundle_id", "")
                                
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
                                # Use selected App match name for both Android and iOS if available
                                # For Android: pass as android_package_name to ensure consistent naming
                                # For iOS: pass as android_package_name (already prioritized in generate_slot_name)
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
                                
                                # For Pangle, create payload even if slot_name is empty (slot_name is not required)
                                if slot_name or network_key == "pangle":
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
            
            # Clear BigOAds apps cache after preview generation is complete
            from components import create_app_helpers
            create_app_helpers._bigoads_apps_cache = None
            
            # Store preview_data in session state
            st.session_state.preview_data = preview_data
            
            # Display previews
            for network_key, preview_info in preview_data.items():
                network_display = preview_info["display"]
                
                # AppLovin: Show info message instead of payload
                if preview_info.get("skip_app_creation"):
                    st.markdown(f"#### 📡 {network_display}")
                    st.info(f"💡 {preview_info.get('info_message', '')}")
                    st.warning("⚠️ **주의사항:** 이미 활성화된 앱/플랫폼/광고 형식 조합에 대해서는 이 API를 통해 추가 Ad Unit을 생성할 수 없습니다. 추가 생성은 대시보드에서 직접 진행해주세요.")
                    st.markdown("---")
                    continue
                
                if "error" in preview_info:
                    st.error(f"❌ **{network_display}**: {preview_info['error']}")
                    with st.expander(f"📋 {network_display} - 매핑된 파라미터", expanded=False):
                        st.json(preview_info["params"])
                else:
                    st.markdown(f"#### 📡 {network_display}")
                    
                    # Show mapped parameters
                    with st.expander(f"📋 {network_display} - 매핑된 파라미터", expanded=False):
                        st.json(preview_info["params"])
                    
                    # Show payloads
                    for platform, payload in preview_info["payloads"].items():
                        if "error" in payload:
                            st.error(f"⚠️ {platform} Payload 생성 실패: {payload['error']}")
                        else:
                            platform_label = platform if platform != "default" else "Default"
                            with st.expander(f"📤 {network_display} - {platform_label} App Payload", expanded=False):
                                st.json(payload)
                    
                    # Show ad unit payloads if available
                    unit_payloads = preview_info.get("unit_payloads", {})
                    if unit_payloads:
                        for platform, platform_units in unit_payloads.items():
                            platform_label = platform if platform != "default" else "Default"
                            with st.expander(f"📦 {network_display} - {platform_label} Ad Unit Payloads (RV, IS, BN)", expanded=False):
                                st.info("💡 `{APP_CODE}`는 앱 생성 후 실제 App ID로 자동 교체됩니다.")
                                for slot_type, unit_payload in platform_units.items():
                                    st.markdown(f"**{slot_type} Unit:**")
                                    st.json(unit_payload)
                    
                    st.markdown("---")
            
            if has_errors:
                st.warning("⚠️ 일부 네트워크에 오류가 있습니다. 문제를 해결한 후 다시 시도해주세요.")
                st.info("💡 일부 네트워크는 추가 정보가 필요할 수 있습니다. 기존 Create App 페이지를 사용해주세요.")
            
            st.divider()
            
            # Step 4: Create Apps
            st.markdown("### 4️⃣ 앱 생성")
            
            create_button = st.button("🚀 선택한 네트워크에 앱 생성", type="primary", width='stretch', disabled=has_errors)
            
            if create_button:
                # Initialize results tracking
                if "creation_results" not in st.session_state:
                    st.session_state.creation_results = {}
                
                # Track success count
                success_count = 0
                total_count = 0
                
                # Get preview_data from session state (created in preview section)
                preview_data = st.session_state.get("preview_data", {})
                
                # Process each network sequentially using preview_data
                for network_key in selected_networks:
                    network_display = available_networks[network_key]
                    config = get_network_config(network_key)
                    preview_info = preview_data.get(network_key)
                    
                    # Skip AppLovin (no app creation)
                    if network_key == "applovin":
                        continue
                    
                    if not preview_info or "error" in preview_info:
                        st.warning(f"⚠️ {network_display}: {preview_info.get('error', '알 수 없는 오류') if preview_info else '미리보기 데이터 없음'}")
                        continue
                    
                    st.markdown(f"#### 📡 {network_display} 처리 중...")
                    
                    # Use mapped params and payloads from preview
                    mapped_params = preview_info["params"]
                    payloads = preview_info["payloads"]
                    
                    # Create app for each platform using preview payloads
                    try:
                        network_manager = get_network_manager()
                        
                        # Handle networks that support both iOS and Android
                        if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "mintegral", "pangle", "vungle"]:
                            results = []
                            
                            # Android
                            if "Android" in payloads:
                                android_payload = payloads["Android"]
                                if "error" in android_payload:
                                    st.error(f"❌ {network_display} - Android: {android_payload['error']}")
                                else:
                                    # Validate payload for IronSource
                                    if network_key == "ironsource":
                                        # Check required fields
                                        required_fields = ["appName", "platform", "storeUrl", "taxonomy"]
                                        missing_fields = [field for field in required_fields if not android_payload.get(field)]
                                        if missing_fields:
                                            st.error(f"❌ {network_display} - Android: 필수 필드 누락: {', '.join(missing_fields)}")
                                            logger.error(f"IronSource Android payload missing fields: {missing_fields}. Payload: {android_payload}")
                                            continue
                                        
                                        # Validate storeUrl is not empty
                                        if not android_payload.get("storeUrl", "").strip():
                                            st.error(f"❌ {network_display} - Android: storeUrl이 비어있습니다.")
                                            logger.error(f"IronSource Android payload has empty storeUrl. Payload: {android_payload}")
                                            continue
                                        
                                        # Log payload for debugging
                                        logger.info(f"IronSource Android payload: {android_payload}")
                                    
                                    with st.spinner(f"{network_display} - Android 앱 생성 중..."):
                                        android_response = network_manager.create_app(network_key, android_payload)
                                    
                                    if android_response:
                                        # Check if response is successful (status: 0)
                                        is_success = android_response.get('status') == 0 or android_response.get('code') == 0
                                        total_count += 1
                                        
                                        android_result = handle_api_response(android_response, network=network_key)
                                        if android_result:
                                            results.append(("Android", android_result, android_response))
                                            
                                            # Track result
                                            app_name = mapped_params.get("name") or mapped_params.get("appName") or mapped_params.get("app_name", "Unknown")
                                            if network_key not in st.session_state.creation_results:
                                                st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                            st.session_state.creation_results[network_key]["apps"].append({
                                                "platform": "Android",
                                                "app_name": app_name,
                                                "success": is_success
                                            })
                                            
                                            st.success(f"✅ {network_display} - Android 앱 생성 성공!")
                                            if is_success:
                                                success_count += 1
                                            
                                                # Immediately create ad units after app creation success
                                                create_ad_units_immediately(
                                                    network_key, network_display, android_response, mapped_params,
                                                    "Android", config, network_manager, app_name
                                                )
                                            
                                            # Show result (no masking for Vungle to show actual response)
                                            with st.expander(f"📥 {network_display} - Android 응답", expanded=False):
                                                if network_key == "vungle":
                                                    st.json(android_response)
                                                else:
                                                    st.json(mask_sensitive_data(android_response))
                                            
                            # iOS
                            if "iOS" in payloads:
                                ios_payload = payloads["iOS"]
                                if "error" in ios_payload:
                                    st.error(f"❌ {network_display} - iOS: {ios_payload['error']}")
                                else:
                                    # Validate payload for IronSource
                                    if network_key == "ironsource":
                                        # Check required fields
                                        required_fields = ["appName", "platform", "storeUrl", "taxonomy"]
                                        missing_fields = [field for field in required_fields if not ios_payload.get(field)]
                                        if missing_fields:
                                            st.error(f"❌ {network_display} - iOS: 필수 필드 누락: {', '.join(missing_fields)}")
                                            logger.error(f"IronSource iOS payload missing fields: {missing_fields}. Payload: {ios_payload}")
                                            continue
                                        
                                        # Validate storeUrl is not empty
                                        if not ios_payload.get("storeUrl", "").strip():
                                            st.error(f"❌ {network_display} - iOS: storeUrl이 비어있습니다.")
                                            logger.error(f"IronSource iOS payload has empty storeUrl. Payload: {ios_payload}")
                                            continue
                                        
                                        # Log payload for debugging
                                        logger.info(f"IronSource iOS payload: {ios_payload}")
                                    
                                    with st.spinner(f"{network_display} - iOS 앱 생성 중..."):
                                        ios_response = network_manager.create_app(network_key, ios_payload)
                                    
                                    if ios_response:
                                        # Check if response is successful (status: 0)
                                        is_success = ios_response.get('status') == 0 or ios_response.get('code') == 0
                                        total_count += 1
                                        
                                        ios_result = handle_api_response(ios_response, network=network_key)
                                        if ios_result:
                                            results.append(("iOS", ios_result, ios_response))
                                            
                                            # Track result
                                            app_name = mapped_params.get("name") or mapped_params.get("appName") or mapped_params.get("app_name", "Unknown")
                                            if network_key not in st.session_state.creation_results:
                                                st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                            st.session_state.creation_results[network_key]["apps"].append({
                                                "platform": "iOS",
                                                "app_name": app_name,
                                                "success": is_success
                                            })
                                            
                                            st.success(f"✅ {network_display} - iOS 앱 생성 성공!")
                                            if is_success:
                                                success_count += 1
                                            
                                                # Immediately create ad units after app creation success
                                                create_ad_units_immediately(
                                                    network_key, network_display, ios_response, mapped_params,
                                                    "iOS", config, network_manager, app_name
                                                )
                                            
                                            # Show result (no masking for Vungle to show actual response)
                                            with st.expander(f"📥 {network_display} - iOS 응답", expanded=False):
                                                if network_key == "vungle":
                                                    st.json(ios_response)
                                                else:
                                                    st.json(mask_sensitive_data(ios_response))
                            
                            if results:
                                # Store response and results
                                st.session_state[f"{network_key}_last_app_response"] = results[-1][2]
                                st.session_state[f"{network_key}_create_app_results"] = results
                                
                                # Process results (similar to existing logic)
                                from components.create_app_ui import (
                                    _process_ironsource_create_app_results,
                                    _process_inmobi_create_app_results,
                                    _process_bigoads_create_app_results,
                                    _process_fyber_create_app_results,
                                    _process_create_app_result
                                )
                                
                                if network_key == "ironsource":
                                    _process_ironsource_create_app_results(
                                        network_key, network_display, mapped_params, results
                                    )
                                elif network_key == "inmobi":
                                    _process_inmobi_create_app_results(
                                        network_key, network_display, mapped_params, results
                                    )
                                elif network_key == "bigoads":
                                    _process_bigoads_create_app_results(
                                        network_key, network_display, mapped_params, results
                                    )
                                elif network_key == "fyber":
                                    _process_fyber_create_app_results(
                                        network_key, network_display, mapped_params, results
                                    )
                                elif network_key == "pangle":
                                    # Pangle: process each platform separately (similar to Mintegral)
                                    for platform, result, response in results:
                                        platform_params = mapped_params.copy()
                                        _process_create_app_result(
                                            network_key, network_display, platform_params, result
                                    )
                                elif network_key == "mintegral":
                                    # Mintegral: process each platform separately
                                    for platform, result, response in results:
                                        # Build platform-specific form_data for processing
                                        platform_params = mapped_params.copy()
                                        if platform == "Android":
                                            platform_params["os"] = "ANDROID"
                                            platform_params["package"] = mapped_params.get("android_package", "")
                                        elif platform == "iOS":
                                            platform_params["os"] = "IOS"
                                            platform_params["package"] = mapped_params.get("ios_package", "")
                                        
                                        _process_create_app_result(
                                            network_key, network_display, platform_params, result
                                        )
                                elif network_key == "vungle":
                                    # Vungle: process each platform separately (similar to Mintegral/Pangle)
                                    for platform, result, response in results:
                                        platform_params = mapped_params.copy()
                                        _process_create_app_result(
                                            network_key, network_display, platform_params, result
                                        )
                        else:
                            # Single platform or other networks
                            if "default" in payloads:
                                payload = payloads["default"]
                                if "error" in payload:
                                    st.error(f"❌ {network_display}: {payload['error']}")
                                else:
                                    with st.spinner(f"{network_display} 앱 생성 중..."):
                                        response = network_manager.create_app(network_key, payload)
                                
                                # Store response
                                st.session_state[f"{network_key}_last_app_response"] = response
                                
                                # Check if response is successful (status: 0)
                                is_success = response.get('status') == 0 or response.get('code') == 0
                                total_count += 1
                                
                                result = handle_api_response(response)
                                
                                if result:
                                    # Track result
                                    app_name = mapped_params.get("name") or mapped_params.get("appName") or mapped_params.get("app_name", "Unknown")
                                    platform_str = mapped_params.get("platformStr", "android") or "android"
                                    platform_display = "Android" if platform_str.lower() == "android" else "iOS"
                                    if network_key not in st.session_state.creation_results:
                                        st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                    st.session_state.creation_results[network_key]["apps"].append({
                                        "platform": platform_display,
                                        "app_name": app_name,
                                        "success": is_success
                                    })
                                    
                                    st.success(f"✅ {network_display} 앱 생성 성공!")
                                    if is_success:
                                        success_count += 1
                                    
                                    # Show result
                                    with st.expander(f"📥 {network_display} 응답", expanded=False):
                                        st.json(mask_sensitive_data(response))
                                    
                                    # Process result
                                    from components.create_app_ui import _process_create_app_result
                                    _process_create_app_result(
                                        network_key, network_display, mapped_params, result
                                    )
                    
                    except Exception as e:
                        st.error(f"❌ {network_display} 앱 생성 실패: {str(e)}")
                        logger.error(f"Error creating app for {network_key}: {str(e)}", exc_info=True)
                        total_count += 1
                    
                    st.markdown("---")
                
                # Show balloons for success, rain for failures
                if success_count > 0:
                    st.balloons()
                    st.success(f"🎉 {success_count}개 네트워크 앱 생성 성공!")
                
                # Check if there are any failures (status: 1)
                failure_count = total_count - success_count
                if failure_count > 0:
                    # Show red flash effect (3 times) for failures
                    st.markdown("""
                    <style>
                    @keyframes redFlash {
                        0% { opacity: 0; }
                        5% { opacity: 0.3; }
                        10% { opacity: 0; }
                        15% { opacity: 0.3; }
                        20% { opacity: 0; }
                        25% { opacity: 0.3; }
                        30% { opacity: 0; }
                        100% { opacity: 0; display: none; }
                    }
                    .red-flash-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(255, 0, 0, 0.3);
                        animation: redFlash 1.5s ease-in-out forwards;
                        pointer-events: none;
                        z-index: 9999;
                    }
                    </style>
                    <div class="red-flash-overlay" id="redFlashOverlay"></div>
                    <script>
                    setTimeout(function() {
                        const overlay = document.getElementById('redFlashOverlay');
                        if (overlay) {
                            overlay.style.display = 'none';
                        }
                    }, 1500);
                    </script>
                    """, unsafe_allow_html=True)
                    st.error(f"⚡ {failure_count}개 네트워크 앱 생성 실패 (status: 1)")
                
                if success_count == 0 and failure_count == 0:
                    st.warning("⚠️ 모든 네트워크 처리 완료 (성공한 앱이 없습니다)")
                
                # Show Create Unit section if any apps were created successfully OR AppLovin is selected
                # AppLovin doesn't require app creation, so show Create Unit section if selected
                # Also check session state to persist across reruns
                created_apps_in_session = st.session_state.get("created_apps_by_network", {})
                show_create_unit = success_count > 0 or "applovin" in selected_networks or bool(created_apps_in_session)
                
                # Initialize created_apps_by_network outside the if block to avoid UnboundLocalError
                # Use session state to persist data across reruns
                if "created_apps_by_network" not in st.session_state:
                    st.session_state.created_apps_by_network = {}
                created_apps_by_network = st.session_state.created_apps_by_network
                
                if show_create_unit:
                    st.divider()
                    st.markdown("### 5️⃣ Create Unit")
                    st.markdown("생성된 앱에 Ad Unit을 추가로 생성할 수 있습니다.")
                    
                    # Add "Create All Units" button at the top
                    st.markdown("#### 🚀 전체 네트워크 Ad Unit 일괄 생성")
                    st.info("💡 모든 네트워크의 모든 Ad Unit (RV, IS, BN)을 한번에 생성합니다.")
                    
                    if st.button(
                        "✅ Create All Units for All Networks (RV, IS, BN)",
                        key="create_all_units_all_networks",
                        width='stretch',
                        type="primary"
                    ):
                        # Collect all units to create from all networks
                        all_units_to_create = []
                        
                        # Iterate through all created apps
                        for network_key, app_data in created_apps_by_network.items():
                            network_display = get_network_display_names().get(network_key, network_key.title())
                            config = get_network_config(network_key)
                            
                            if not config:
                                continue
                            
                            # Get mapped_params from preview_data if not in app_data
                            mapped_params = app_data.get("mapped_params", {})
                            if not mapped_params:
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                            
                            # Extract app info for this network
                            app_info = extract_app_info_from_response(network_key, app_data.get("response"), mapped_params)
                            
                            if not app_info:
                                continue
                            
                            app_name = app_info.get("name", "Unknown")
                            app_code = app_info.get("appCode") or app_info.get("appId") or app_info.get("appKey")
                            
                            if not app_code:
                                continue
                            
                            # Handle special cases (Vungle, Unity, IronSource, AppLovin, Pangle)
                            if network_key == "vungle" and app_data.get("results"):
                                # Vungle: handle each platform separately
                                results_list = app_data.get("results", [])
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                                
                                for platform, result, response in results_list:
                                    result_data = response.get("result", {}) if isinstance(response.get("result"), dict) else response
                                    vungle_app_id = result_data.get("vungleAppId") or result_data.get("id")
                                    platform_value = result_data.get("platform", "").lower()
                                    
                                    android_package = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
                                    
                                    if platform_value == "android":
                                        pkg_name = android_package
                                        bundle_id = ""
                                        platform_str_for_unit = "android"
                                        android_package_for_unit = None
                                    elif platform_value == "ios":
                                        pkg_name = ""
                                        bundle_id = mapped_params.get("ios_store_id", mapped_params.get("iosAppId", ""))
                                        platform_str_for_unit = "ios"
                                        # Use user-selected identifier if available
                                        if "ios_ad_unit_identifier" in st.session_state:
                                            android_package_for_unit = st.session_state.ios_ad_unit_identifier.get("value", None)
                                        else:
                                            android_package_for_unit = android_package if android_package else None
                                            # Extract last part if it's a full package name
                                            if android_package_for_unit and '.' in android_package_for_unit:
                                                android_package_for_unit = android_package_for_unit.split('.')[-1]
                                    else:
                                        continue
                                    
                                    # Generate unit names
                                    from components.create_app_helpers import generate_slot_name
                                    network_manager = get_network_manager()
                                    
                                    for slot_type in ["rv", "is", "bn"]:
                                        slot_name = generate_slot_name(
                                            pkg_name,
                                            platform_str_for_unit,
                                            slot_type,
                                            network_key,
                                            bundle_id=bundle_id,
                                            network_manager=network_manager,
                                            app_name=app_name,
                                            android_package_name=android_package_for_unit
                                        )
                                        
                                        if slot_name:
                                            all_units_to_create.append({
                                                "network": network_key,
                                                "network_display": network_display,
                                                "app_info": {
                                                    "vungleAppId": vungle_app_id,
                                                    "platform": platform_value,
                                                    "name": app_name
                                                },
                                                "slot_type": slot_type,
                                                "slot_name": slot_name,
                                                "platform_str": platform_str_for_unit
                                            })
                            elif network_key in ["applovin", "pangle"]:
                                # AppLovin and Pangle: handled separately in their sections
                                # But we can still create units if app_info is available
                                if app_info:
                                    platform_str = app_info.get("platformStr", "android")
                                    pkg_name = app_info.get("pkgName", "")
                                    bundle_id = app_info.get("bundleId", "")
                                    
                                    # For AppLovin, get from app_info
                                    if network_key == "applovin":
                                        android_package = app_info.get("android_package", "")
                                        ios_bundle_id = app_info.get("ios_bundle_id", "")
                                        
                                        # Generate for Android
                                        if android_package:
                                            from components.create_app_helpers import generate_slot_name
                                            network_manager = get_network_manager()
                                            
                                            for slot_type in ["rv", "is", "bn"]:
                                                slot_name = generate_slot_name(
                                                    android_package,
                                                    "android",
                                                    slot_type,
                                                    network_key,
                                                    network_manager=network_manager,
                                                    app_name=app_name
                                                )
                                                
                                                if slot_name:
                                                    all_units_to_create.append({
                                                        "network": network_key,
                                                        "network_display": network_display,
                                                        "app_info": {
                                                            **app_info,
                                                            "package_name": android_package,
                                                            "platform": "android"
                                                        },
                                                        "slot_type": slot_type,
                                                        "slot_name": slot_name,
                                                        "platform_str": "android"
                                                    })
                                        
                                        # Generate for iOS
                                        if ios_bundle_id:
                                            from components.create_app_helpers import generate_slot_name
                                            network_manager = get_network_manager()
                                            
                                            # Use user-selected identifier if available
                                            android_package_for_unit = None
                                            if "ios_ad_unit_identifier" in st.session_state:
                                                android_package_for_unit = st.session_state.ios_ad_unit_identifier.get("value", None)
                                            else:
                                                android_package_for_unit = android_package if android_package else None
                                                # Extract last part if it's a full package name
                                                if android_package_for_unit and '.' in android_package_for_unit:
                                                    android_package_for_unit = android_package_for_unit.split('.')[-1]
                                            
                                            for slot_type in ["rv", "is", "bn"]:
                                                slot_name = generate_slot_name(
                                                    "",
                                                    "ios",
                                                    slot_type,
                                                    network_key,
                                                    bundle_id=ios_bundle_id,
                                                    network_manager=network_manager,
                                                    app_name=app_name,
                                                    android_package_name=android_package_for_unit
                                                )
                                                
                                                if slot_name:
                                                    all_units_to_create.append({
                                                        "network": network_key,
                                                        "network_display": network_display,
                                                        "app_info": {
                                                            **app_info,
                                                            "bundleId": ios_bundle_id,
                                                            "platform": "ios"
                                                        },
                                                        "slot_type": slot_type,
                                                        "slot_name": slot_name,
                                                        "platform_str": "ios"
                                                    })
                                continue
                            elif app_data.get("results"):
                                # Multi-platform networks (IronSource, Pangle, etc.): handle each platform separately
                                results_list = app_data.get("results", [])
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                                
                                for platform, result, response in results_list:
                                    # Extract app info for this specific platform
                                    platform_app_info = extract_app_info_from_response(network_key, response, mapped_params)
                                    
                                    if not platform_app_info:
                                        continue
                                    
                                    # Determine platform
                                    platform_value = platform.lower() if isinstance(platform, str) else "android"
                                    platform_str = "android" if platform_value == "android" else "ios"
                                    
                                    # Get platform-specific package name and bundle ID
                                    android_package = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
                                    
                                    if platform_str == "android":
                                        pkg_name = platform_app_info.get("pkgName", "") or android_package
                                        bundle_id = ""
                                        android_package_for_unit = None
                                    else:
                                        pkg_name = ""
                                        bundle_id = platform_app_info.get("bundleId", "") or mapped_params.get("ios_store_id", mapped_params.get("iosAppId", ""))
                                        android_package_for_unit = android_package if android_package else None
                                    
                                    # Generate unit names
                                    from components.create_app_helpers import generate_slot_name
                                    network_manager = get_network_manager()
                                    
                                    for slot_type in ["rv", "is", "bn"]:
                                        slot_name = generate_slot_name(
                                            pkg_name,
                                            platform_str,
                                            slot_type,
                                            network_key,
                                            bundle_id=bundle_id,
                                            network_manager=network_manager,
                                            app_name=app_name,
                                            android_package_name=android_package_for_unit
                                        )
                                        
                                        if slot_name:
                                            all_units_to_create.append({
                                                "network": network_key,
                                                "network_display": network_display,
                                                "app_info": {
                                                    **platform_app_info,
                                                    "platform": platform_value,
                                                    "name": app_name
                                                },
                                                "slot_type": slot_type,
                                                "slot_name": slot_name,
                                                "platform_str": platform_str
                                            })
                            else:
                                # Single-platform networks: create RV, IS, BN
                                platform_str = app_info.get("platformStr", "android")
                                
                                # Get package name and bundle ID
                                pkg_name = app_info.get("pkgName", "")
                                bundle_id = app_info.get("bundleId", "")
                                
                                # For iOS, use user-selected identifier if available
                                android_package_for_unit = None
                                if platform_str == "ios":
                                    if "ios_ad_unit_identifier" in st.session_state:
                                        # Use user-selected value
                                        android_package_for_unit = st.session_state.ios_ad_unit_identifier.get("value", None)
                                    else:
                                        # Fallback: try to get from mapped_params
                                        preview_info = preview_data.get(network_key, {})
                                        mapped_params = preview_info.get("params", {})
                                        android_package_for_unit = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
                                        # Extract last part if it's a full package name
                                        if android_package_for_unit and '.' in android_package_for_unit:
                                            android_package_for_unit = android_package_for_unit.split('.')[-1]
                                
                                # Generate unit names
                                from components.create_app_helpers import generate_slot_name
                                network_manager = get_network_manager()
                                
                                for slot_type in ["rv", "is", "bn"]:
                                    slot_name = generate_slot_name(
                                        pkg_name,
                                        platform_str,
                                        slot_type,
                                        network_key,
                                        bundle_id=bundle_id,
                                        network_manager=network_manager,
                                        app_name=app_name,
                                        android_package_name=android_package_for_unit
                                    )
                                    
                                    if slot_name:
                                        all_units_to_create.append({
                                            "network": network_key,
                                            "network_display": network_display,
                                            "app_info": app_info,
                                            "slot_type": slot_type,
                                            "slot_name": slot_name,
                                            "platform_str": platform_str
                                        })
                        
                        # Create all units
                        if all_units_to_create:
                            total_units = len(all_units_to_create)
                            success_count = 0
                            failure_count = 0
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, unit_info in enumerate(all_units_to_create):
                                network_key = unit_info["network"]
                                network_display = unit_info["network_display"]
                                app_info = unit_info["app_info"]
                                slot_type = unit_info["slot_type"]
                                slot_name = unit_info["slot_name"]
                                platform_str = unit_info["platform_str"]
                                
                                progress = (idx + 1) / total_units
                                progress_bar.progress(progress)
                                status_text.text(f"생성 중: {network_display} - {slot_type.upper()} ({idx + 1}/{total_units})")
                                
                                try:
                                    network_manager = get_network_manager()
                                    config = get_network_config(network_key)
                                    
                                    if network_key == "vungle":
                                        # Vungle: use create_unit with special handling
                                        vungle_app_id = app_info.get("vungleAppId")
                                        platform_value = app_info.get("platform", "")
                                        
                                        # Deactivate existing placements first
                                        if vungle_app_id:
                                            try:
                                                existing_placements = network_manager._get_vungle_placements_by_app_id(str(vungle_app_id))
                                                for placement in existing_placements:
                                                    initial_placement_id = placement.get("id")
                                                    if initial_placement_id:
                                                        # Get full placement details to get accurate ID
                                                        placement_details = network_manager._vungle_api.get_placement(str(initial_placement_id))
                                                        if placement_details and placement_details.get("result"):
                                                            placement_id = placement_details["result"].get("id")
                                                            if placement_id:
                                                                network_manager._vungle_api.update_placement(str(placement_id), {"status": "inactive"})
                                            except Exception as e:
                                                logger.warning(f"[Vungle] Failed to deactivate existing placements: {str(e)}")
                                        
                                        # Create unit payload
                                        unit_payload = config.build_unit_payload(
                                            app_id=str(vungle_app_id),
                                            unit_name=slot_name,
                                            ad_type=slot_type,
                                            platform=platform_value
                                        )
                                        
                                        response = network_manager.create_unit(network_key, unit_payload)
                                    elif network_key == "applovin":
                                        # AppLovin: use create_unit with special payload
                                        ad_format_map = {"rv": "REWARD", "is": "INTER", "bn": "BANNER"}
                                        ad_format = ad_format_map.get(slot_type.lower(), "REWARD")
                                        
                                        unit_payload = {
                                            "name": slot_name,
                                            "platform": platform_str,
                                            "ad_format": ad_format
                                        }
                                        
                                        if platform_str == "android":
                                            unit_payload["package_name"] = app_info.get("package_name", "")
                                        else:
                                            unit_payload["bundle_id"] = app_info.get("bundleId", "")
                                        
                                        response = network_manager.create_unit(network_key, unit_payload)
                                    else:
                                        # Standard networks: use create_default_slot
                                        from components.create_app_helpers import create_default_slot
                                        create_default_slot(
                                            network_key,
                                            app_info,
                                            slot_type,
                                            network_manager,
                                            config
                                        )
                                        response = {"status": 0}  # Assume success if no exception
                                    
                                    success_count += 1
                                    
                                    # Track unit creation result
                                    platform_display = "Android" if platform_str.lower() == "android" else "iOS"
                                    if network_key not in st.session_state.creation_results:
                                        st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                    st.session_state.creation_results[network_key]["units"].append({
                                        "platform": platform_display,
                                        "app_name": app_info.get("name", "Unknown"),
                                        "unit_name": slot_name,
                                        "unit_type": slot_type.upper(),
                                        "success": True
                                    })
                                    
                                except Exception as e:
                                    failure_count += 1
                                    
                                    # Track unit creation failure
                                    platform_display = "Android" if platform_str.lower() == "android" else "iOS"
                                    if network_key not in st.session_state.creation_results:
                                        st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                    st.session_state.creation_results[network_key]["units"].append({
                                        "platform": platform_display,
                                        "app_name": app_info.get("name", "Unknown"),
                                        "unit_name": slot_name,
                                        "unit_type": slot_type.upper(),
                                        "success": False,
                                        "error": str(e)
                                    })
                                    
                                    logger.error(f"Error creating {slot_type} unit for {network_key}: {str(e)}", exc_info=True)
                            
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Show summary
                            if success_count == total_units:
                                st.balloons()
                                st.success(f"🎉 모든 Ad Unit 생성 완료! ({success_count}/{total_units})")
                            elif success_count > 0:
                                st.warning(f"⚠️ {success_count}/{total_units}개 Ad Unit 생성 완료, {failure_count}개 실패")
                            else:
                                st.error(f"❌ 모든 Ad Unit 생성 실패 ({failure_count}/{total_units})")
                            
                            # Force rerun to update UI
                            st.rerun()
                        else:
                            st.warning("⚠️ 생성할 Ad Unit이 없습니다. 먼저 App을 생성해주세요.")
                    
                    st.divider()
                    
                    # Get preview_data from session state
                    preview_data = st.session_state.get("preview_data", {})
                    
                    # Get successfully created apps from session state and responses
                    # For multi-platform networks, we need to check results list
                    for network_key in selected_networks:
                        # First try SessionManager
                        last_app_info = SessionManager.get_last_created_app_info(network_key)
                        
                        # Get response to check success and extract info
                        response_key = f"{network_key}_last_app_response"
                        response = st.session_state.get(response_key)
                        
                        # For multi-platform networks, check if we have results stored
                        results_key = f"{network_key}_create_app_results"
                        results = st.session_state.get(results_key, [])
                        
                        if response and isinstance(response, dict):
                            is_success = response.get('status') == 0 or response.get('code') == 0
                            if is_success:
                                # Extract app info from response
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                                
                                # For IronSource and other multi-platform networks, use results if available
                                if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "mintegral", "pangle", "vungle"] and results:
                                    # Use results from multi-platform creation
                                    extracted_info = None
                                    # Try to extract from first result
                                    if results and len(results) > 0:
                                        platform, result, resp = results[0]
                                        extracted_info = extract_app_info_from_response(network_key, resp, mapped_params)
                                else:
                                    extracted_info = extract_app_info_from_response(network_key, response, mapped_params)
                                
                                if extracted_info:
                                    # Merge with SessionManager info if available
                                    if last_app_info:
                                        extracted_info.update(last_app_info)
                                    
                                    created_apps_by_network[network_key] = {
                                        "display": available_networks[network_key],
                                        "app_info": extracted_info,
                                        "response": response,
                                        "results": results if results else None
                                    }
                                    # Update session state to persist data
                                    st.session_state.created_apps_by_network = created_apps_by_network
                
                # Add AppLovin to created_apps_by_network if selected (even without app creation)
                if "applovin" in selected_networks and "applovin" not in created_apps_by_network:
                    # Get store info for AppLovin
                    app_name = None
                    android_package = None
                    ios_bundle_id = None
                    
                    if st.session_state.store_info_android:
                        android_info = st.session_state.store_info_android
                        app_name = android_info.get("name", "")
                        android_package = android_info.get("package_name", "")
                    
                    if st.session_state.store_info_ios:
                        ios_info = st.session_state.store_info_ios
                        if not app_name:
                            app_name = ios_info.get("name", "")
                        ios_bundle_id = ios_info.get("bundle_id", "")
                    
                    if app_name:
                        created_apps_by_network["applovin"] = {
                            "display": available_networks["applovin"],
                            "app_info": {
                                "name": app_name,
                                "android_package": android_package,
                                "ios_bundle_id": ios_bundle_id
                            },
                            "response": None,
                            "is_applovin": True  # Flag to indicate this is AppLovin (no app creation)
                        }
                
                if created_apps_by_network:
                        for network_key, app_data in created_apps_by_network.items():
                            network_display = app_data["display"]
                            app_info = app_data["app_info"]
                            response = app_data.get("response", {})
                            is_applovin = app_data.get("is_applovin", False)
                            
                            st.markdown(f"#### 📡 {network_display}")
                            
                            # Check if network supports unit creation
                            config = get_network_config(network_key)
                            if not config.supports_create_unit():
                                st.info(f"💡 {network_display}는 Unit 생성 기능을 지원하지 않습니다.")
                                continue
                            
                            # AppLovin: Special handling (no app creation, use store info directly)
                            if is_applovin:
                                st.info("💡 AppLovin은 API를 통한 앱 생성 기능을 지원하지 않습니다. 대시보드에서 앱을 생성한 후, 아래에서 Ad Unit을 생성할 수 있습니다.")
                                st.warning("⚠️ **주의사항:** 이미 활성화된 앱/플랫폼/광고 형식 조합에 대해서는 이 API를 통해 추가 Ad Unit을 생성할 수 없습니다. 추가 생성은 대시보드에서 직접 진행해주세요.")
                                
                                app_name = app_info.get("name", "Unknown")
                                android_package = app_info.get("android_package", "")
                                ios_bundle_id = app_info.get("ios_bundle_id", "")
                                
                                st.markdown(f"**앱 정보:** {app_name}")
                                
                                from components.create_app_helpers import generate_slot_name
                                network_manager = get_network_manager()
                                
                                # Show Ad Unit creation for each platform
                                platform_cols = st.columns(2)
                                
                                # Android Ad Units
                                with platform_cols[0]:
                                    if android_package:
                                        st.markdown("##### 🤖 Android")
                                        st.text(f"**Package Name:** {android_package}")
                                        
                                        # Generate unit names for RV, IS, BN
                                        android_units = {}
                                        for slot_type, ad_format in [("rv", "REWARD"), ("is", "INTER"), ("bn", "BANNER")]:
                                            unit_name = generate_slot_name(
                                                android_package,
                                                "android",
                                                slot_type,
                                                "applovin",
                                                network_manager=network_manager,
                                                app_name=app_name
                                            ) or f"{app_name}_{ad_format.lower()}"
                                            android_units[ad_format] = {
                                                "name": unit_name,
                                                "slot_type": slot_type
                                            }
                                        
                                        # Display unit names preview
                                        st.markdown("**생성될 Ad Unit 이름:**")
                                        for ad_format, unit_info in android_units.items():
                                            st.text_input(
                                                f"{ad_format} Unit Name",
                                                value=unit_info["name"],
                                                key=f"applovin_android_{ad_format.lower()}_name",
                                                disabled=True
                                            )
                                        
                                        # Create all units button
                                        if st.button(
                                            "✅ Create All Android Units (RV, IS, BN)",
                                            key=f"create_applovin_android_all",
                                            width='stretch',
                                            type="primary"
                                        ):
                                            success_count_android = 0
                                            failure_count_android = 0
                                            
                                            for ad_format, unit_info in android_units.items():
                                                try:
                                                    unit_name = st.session_state.get(f"applovin_android_{ad_format.lower()}_name", unit_info["name"])
                                                    unit_payload = {
                                                        "name": unit_name,
                                                        "platform": "android",
                                                        "package_name": android_package,
                                                        "ad_format": ad_format
                                                    }
                                                    
                                                    with st.spinner(f"Creating Android {ad_format}..."):
                                                        response = network_manager.create_unit("applovin", unit_payload)
                                                        
                                                    if response and (response.get('status') == 0 or response.get('code') == 0):
                                                        success_count_android += 1
                                                        
                                                        # Track unit creation result
                                                        if "applovin" not in st.session_state.creation_results:
                                                            st.session_state.creation_results["applovin"] = {"network": "AppLovin", "apps": [], "units": []}
                                                        st.session_state.creation_results["applovin"]["units"].append({
                                                            "platform": "Android",
                                                            "app_name": app_name,
                                                            "unit_name": unit_name,
                                                            "unit_type": ad_format,
                                                            "success": True
                                                        })
                                                        
                                                        st.success(f"✅ Android {ad_format} Unit 생성 완료!")
                                                    else:
                                                        failure_count_android += 1
                                                        
                                                        # Track unit creation failure
                                                        if "applovin" not in st.session_state.creation_results:
                                                            st.session_state.creation_results["applovin"] = {"network": "AppLovin", "apps": [], "units": []}
                                                        st.session_state.creation_results["applovin"]["units"].append({
                                                            "platform": "Android",
                                                            "app_name": app_name,
                                                            "unit_name": unit_name,
                                                            "unit_type": ad_format,
                                                            "success": False,
                                                            "error": response.get("msg", "Unknown error") if response else "No response"
                                                        })
                                                        
                                                        st.error(f"❌ Android {ad_format} Unit 생성 실패")
                                                        if response:
                                                            with st.expander(f"Error Details - {ad_format}", expanded=False):
                                                                st.json(mask_sensitive_data(response))
                                                except Exception as e:
                                                    failure_count_android += 1
                                                    st.error(f"❌ Android {ad_format} 오류: {str(e)}")
                                                    logger.error(f"Error creating AppLovin Android {ad_format} unit: {str(e)}", exc_info=True)
                                            
                                            # Summary
                                            if success_count_android == 3:
                                                st.balloons()
                                                st.success(f"🎉 Android 모든 Unit 생성 완료! (RV, IS, BN)")
                                            elif success_count_android > 0:
                                                st.warning(f"⚠️ Android {success_count_android}/3 Unit 생성 완료, {failure_count_android}개 실패")
                                            else:
                                                st.error(f"❌ Android 모든 Unit 생성 실패")
                                
                                # iOS Ad Units
                                with platform_cols[1]:
                                    if ios_bundle_id:
                                        st.markdown("##### 🍎 iOS")
                                        st.text(f"**Bundle ID:** {ios_bundle_id}")
                                        
                                        # Generate unit names for RV, IS, BN
                                        ios_units = {}
                                        for slot_type, ad_format in [("rv", "REWARD"), ("is", "INTER"), ("bn", "BANNER")]:
                                            # Use user-selected identifier if available for AppLovin iOS units
                                            android_package_for_applovin = None
                                            if "ios_ad_unit_identifier" in st.session_state:
                                                android_package_for_applovin = st.session_state.ios_ad_unit_identifier.get("value", None)
                                            else:
                                                android_package_for_applovin = android_package if android_package else None
                                                # Extract last part if it's a full package name
                                                if android_package_for_applovin and '.' in android_package_for_applovin:
                                                    android_package_for_applovin = android_package_for_applovin.split('.')[-1]
                                            
                                            unit_name = generate_slot_name(
                                                "",  # pkg_name is empty for iOS
                                                "ios",
                                                slot_type,
                                                "applovin",
                                                bundle_id=ios_bundle_id,
                                                network_manager=network_manager,
                                                app_name=app_name,
                                                android_package_name=android_package_for_applovin
                                            ) or f"{app_name}_{ad_format.lower()}"
                                            ios_units[ad_format] = {
                                                "name": unit_name,
                                                "slot_type": slot_type
                                            }
                                        
                                        # Display unit names preview
                                        st.markdown("**생성될 Ad Unit 이름:**")
                                        for ad_format, unit_info in ios_units.items():
                                            st.text_input(
                                                f"{ad_format} Unit Name",
                                                value=unit_info["name"],
                                                key=f"applovin_ios_{ad_format.lower()}_name",
                                                disabled=True
                                            )
                                        
                                        # Create all units button
                                        if st.button(
                                            "✅ Create All iOS Units (RV, IS, BN)",
                                            key=f"create_applovin_ios_all",
                                            width='stretch',
                                            type="primary"
                                        ):
                                            success_count_ios = 0
                                            failure_count_ios = 0
                                            
                                            for ad_format, unit_info in ios_units.items():
                                                try:
                                                    unit_name = st.session_state.get(f"applovin_ios_{ad_format.lower()}_name", unit_info["name"])
                                                    unit_payload = {
                                                        "name": unit_name,
                                                        "platform": "ios",
                                                        "package_name": ios_bundle_id,
                                                        "ad_format": ad_format
                                                    }
                                                    
                                                    with st.spinner(f"Creating iOS {ad_format}..."):
                                                        response = network_manager.create_unit("applovin", unit_payload)
                                                        
                                                    if response and (response.get('status') == 0 or response.get('code') == 0):
                                                        success_count_ios += 1
                                                        
                                                        # Track unit creation result
                                                        if "applovin" not in st.session_state.creation_results:
                                                            st.session_state.creation_results["applovin"] = {"network": "AppLovin", "apps": [], "units": []}
                                                        st.session_state.creation_results["applovin"]["units"].append({
                                                            "platform": "iOS",
                                                            "app_name": app_name,
                                                            "unit_name": unit_name_ios,
                                                            "unit_type": ad_format,
                                                            "success": True
                                                        })
                                                        
                                                        st.success(f"✅ iOS {ad_format} Unit 생성 완료!")
                                                    else:
                                                        failure_count_ios += 1
                                                        
                                                        # Track unit creation failure
                                                        if "applovin" not in st.session_state.creation_results:
                                                            st.session_state.creation_results["applovin"] = {"network": "AppLovin", "apps": [], "units": []}
                                                        st.session_state.creation_results["applovin"]["units"].append({
                                                            "platform": "iOS",
                                                            "app_name": app_name,
                                                            "unit_name": unit_name_ios,
                                                            "unit_type": ad_format,
                                                            "success": False,
                                                            "error": response.get("msg", "Unknown error") if response else "No response"
                                                        })
                                                        
                                                        st.error(f"❌ iOS {ad_format} Unit 생성 실패")
                                                        if response:
                                                            with st.expander(f"Error Details - {ad_format}", expanded=False):
                                                                st.json(mask_sensitive_data(response))
                                                except Exception as e:
                                                    failure_count_ios += 1
                                                    
                                                    # Track unit creation exception
                                                    if "applovin" not in st.session_state.creation_results:
                                                        st.session_state.creation_results["applovin"] = {"network": "AppLovin", "apps": [], "units": []}
                                                    st.session_state.creation_results["applovin"]["units"].append({
                                                        "platform": "iOS",
                                                        "app_name": app_name,
                                                        "unit_name": unit_name_ios,
                                                        "unit_type": ad_format,
                                                        "success": False,
                                                        "error": str(e)
                                                    })
                                                    
                                                    st.error(f"❌ iOS {ad_format} 오류: {str(e)}")
                                                    logger.error(f"Error creating AppLovin iOS {ad_format} unit: {str(e)}", exc_info=True)
                                            
                                            # Summary
                                            if success_count_ios == 3:
                                                st.balloons()
                                                st.success(f"🎉 iOS 모든 Unit 생성 완료! (RV, IS, BN)")
                                            elif success_count_ios > 0:
                                                st.warning(f"⚠️ iOS {success_count_ios}/3 Unit 생성 완료, {failure_count_ios}개 실패")
                                            else:
                                                st.error(f"❌ iOS 모든 Unit 생성 실패")
                                
                                st.markdown("---")
                                continue
                            
                            # Get app info
                            app_code = app_info.get("appCode") or app_info.get("appId") or app_info.get("appKey")
                            app_name = app_info.get("name", "Unknown")
                            platform_str = app_info.get("platformStr", "android")
                            
                            if not app_code:
                                st.warning(f"⚠️ {network_display}: App Code를 찾을 수 없습니다.")
                                continue
                            
                            # Display app info
                            st.markdown(f"**앱 정보:** {app_name}")
                            
                            # For Vungle, show platform-specific App IDs
                            if network_key == "vungle" and app_data.get("results"):
                                # Vungle: Show Android and iOS App IDs separately
                                results_list = app_data.get("results", [])
                                android_app_id = None
                                ios_app_id = None
                                
                                for platform, result, response in results_list:
                                    result_data = response.get("result", {}) if isinstance(response.get("result"), dict) else response
                                    vungle_app_id = result_data.get("vungleAppId") or result_data.get("id")
                                    if platform == "Android":
                                        android_app_id = vungle_app_id
                                    elif platform == "iOS":
                                        ios_app_id = vungle_app_id
                                
                                info_cols = st.columns(2)
                                with info_cols[0]:
                                    if android_app_id:
                                        st.text(f"**🤖 Android App ID:** {android_app_id}")
                                    else:
                                        st.text("**🤖 Android App ID:** -")
                                with info_cols[1]:
                                    if ios_app_id:
                                        st.text(f"**🍎 iOS App ID:** {ios_app_id}")
                                    else:
                                        st.text("**🍎 iOS App ID:** -")
                            else:
                                # Other networks: show standard app info
                                info_cols = st.columns(3)
                                with info_cols[0]:
                                    st.text(f"**App Code:** {app_code}")
                                with info_cols[1]:
                                    if app_info.get("appId"):
                                        st.text(f"**App ID:** {app_info.get('appId')}")
                                with info_cols[2]:
                                    if app_info.get("appKey"):
                                        st.text(f"**App Key:** {app_info.get('appKey')}")
                            
                            # Archive/Deactivate existing units (if needed)
                            if network_key == "ironsource":
                                # IronSource: Deactivate existing ad units
                                st.markdown("##### ⏸️ 기존 Ad Units 비활성화")
                                st.info("💡 IronSource App 생성 시 기존 Ad Units가 있을 수 있습니다. Create Unit 전에 기존 Ad Units를 deactivate 해야 합니다.")
                                
                                app_key_android = None
                                app_key_ios = None
                                
                                # Extract app keys from results or response
                                results_list = app_data.get("results", [])
                                if results_list:
                                    for platform, result, resp in results_list:
                                        app_key = result.get("appKey") or resp.get("appKey")
                                        if platform == "Android" and app_key:
                                            app_key_android = app_key
                                        elif platform == "iOS" and app_key:
                                            app_key_ios = app_key
                                else:
                                    # Fallback to response
                                    result = response.get('result', {})
                                    if isinstance(result, list) and len(result) > 0:
                                        for item in result:
                                            platform = item.get("platform", "").lower()
                                            app_key = item.get("appKey")
                                            if platform == "android" and app_key:
                                                app_key_android = app_key
                                            elif platform == "ios" and app_key:
                                                app_key_ios = app_key
                                    elif isinstance(result, dict):
                                        app_key = result.get("appKey") or response.get("appKey")
                                        if app_key:
                                            # Try to determine platform from app_info
                                            if app_info.get("platformStr") == "android":
                                                app_key_android = app_key
                                            elif app_info.get("platformStr") == "ios":
                                                app_key_ios = app_key
                                
                                deactivate_cols = st.columns(2)
                                with deactivate_cols[0]:
                                    if app_key_android:
                                        if st.button(f"⏸️ Deactivate Android Units", key=f"deactivate_{network_key}_android"):
                                            try:
                                                from utils.ad_network_query import get_ironsource_units
                                                existing_units = get_ironsource_units(app_key_android)
                                                
                                                if existing_units:
                                                    deactivate_payloads = []
                                                    for unit in existing_units:
                                                        mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                                        if mediation_adunit_id:
                                                            deactivate_payloads.append({
                                                                "mediationAdUnitId": str(mediation_adunit_id).strip(),
                                                                "isPaused": True
                                                            })
                                                    
                                                    if deactivate_payloads:
                                                        deactivate_response = network_manager._update_ironsource_ad_units(app_key_android, deactivate_payloads)
                                                        if deactivate_response.get("status") == 0:
                                                            st.success(f"✅ {len(deactivate_payloads)}개 Android Units 비활성화 완료!")
                                                        else:
                                                            st.error("❌ Android Units 비활성화 실패")
                                                else:
                                                    st.info("⚠️ 비활성화할 Android Units가 없습니다.")
                                            except Exception as e:
                                                st.error(f"❌ 오류: {str(e)}")
                                
                                with deactivate_cols[1]:
                                    if app_key_ios:
                                        if st.button(f"⏸️ Deactivate iOS Units", key=f"deactivate_{network_key}_ios"):
                                            try:
                                                from utils.ad_network_query import get_ironsource_units
                                                existing_units = get_ironsource_units(app_key_ios)
                                                
                                                if existing_units:
                                                    deactivate_payloads = []
                                                    for unit in existing_units:
                                                        mediation_adunit_id = unit.get("mediationAdUnitId") or unit.get("mediationAdunitId") or unit.get("id")
                                                        if mediation_adunit_id:
                                                            deactivate_payloads.append({
                                                                "mediationAdUnitId": str(mediation_adunit_id).strip(),
                                                                "isPaused": True
                                                            })
                                                    
                                                    if deactivate_payloads:
                                                        deactivate_response = network_manager._update_ironsource_ad_units(app_key_ios, deactivate_payloads)
                                                        if deactivate_response.get("status") == 0:
                                                            st.success(f"✅ {len(deactivate_payloads)}개 iOS Units 비활성화 완료!")
                                                        else:
                                                            st.error("❌ iOS Units 비활성화 실패")
                                                else:
                                                    st.info("⚠️ 비활성화할 iOS Units가 없습니다.")
                                            except Exception as e:
                                                st.error(f"❌ 오류: {str(e)}")
                            
                            elif network_key == "unity":
                                # Unity: Archive existing ad units
                                st.markdown("##### 📦 기존 Ad Units Archive")
                                st.info("💡 Unity 프로젝트 생성 시 기본 Ad Units가 자동으로 생성됩니다. Create Unit 전에 기존 Ad Units를 archive해야 합니다.")
                                
                                # Unity archive requires project_id (not gameId)
                                project_id = app_info.get("project_id")
                                if not project_id:
                                    # Try to get from gameId if available
                                    game_id_info = app_info.get("gameId", {})
                                    if isinstance(game_id_info, dict):
                                        project_id = game_id_info.get("project_id")
                                
                                if project_id:
                                    try:
                                        from utils.ad_network_query import get_unity_ad_units
                                        ad_units_data = get_unity_ad_units(project_id)
                                        
                                        archive_cols = st.columns(2)
                                        for idx, (store_name, store_display) in enumerate([("apple", "Apple (iOS)"), ("google", "Google (Android)")]):
                                            with archive_cols[idx]:
                                                store_data = ad_units_data.get(store_name, {})
                                                ad_units = store_data.get("adUnits", {})
                                                
                                                if ad_units:
                                                    ad_unit_names = list(ad_units.keys())
                                                    st.write(f"**{store_display} Units:** {len(ad_unit_names)}개")
                                                    
                                                    if st.button(f"📦 Archive {store_display}", key=f"archive_{network_key}_{store_name}"):
                                                        archive_payload = {}
                                                        for ad_unit_id in ad_units.keys():
                                                            archive_payload[ad_unit_id] = {"archive": True}
                                                        
                                                        archive_response = network_manager._update_unity_ad_units(project_id, store_name, archive_payload)
                                                        if archive_response.get("status") == 0:
                                                            st.success(f"✅ {store_display} Units Archive 완료!")
                                                        else:
                                                            st.error(f"❌ {store_display} Units Archive 실패")
                                                else:
                                                    st.info(f"⚠️ {store_display} Units 없음")
                                    except Exception as e:
                                        st.warning(f"⚠️ Unity Ad Units 조회 실패: {str(e)}")
                            
                            st.divider()
                            
                            # For Vungle, handle each platform separately
                            if network_key == "vungle" and app_data.get("results"):
                                # Vungle: Create units for each platform separately
                                results_list = app_data.get("results", [])
                                
                                # Get mapped_params from preview_data
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                                
                                for platform, result, response in results_list:
                                    result_data = response.get("result", {}) if isinstance(response.get("result"), dict) else response
                                    vungle_app_id = result_data.get("vungleAppId") or result_data.get("id")
                                    platform_value = result_data.get("platform", "").lower()
                                    platform_display = "Android" if platform_value == "android" else "iOS"
                                    
                                    st.markdown(f"##### 📱 {platform_display}")
                                    st.text(f"**App ID:** {vungle_app_id}")
                                    
                                    # Get platform-specific package name/bundle ID
                                    android_package = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
                                    
                                    if platform_value == "android":
                                        pkg_name = android_package
                                        bundle_id = ""
                                        platform_str_for_unit = "android"
                                        android_package_for_unit = None  # Not needed for Android
                                    elif platform_value == "ios":
                                        pkg_name = ""
                                        bundle_id = mapped_params.get("ios_store_id", mapped_params.get("iosAppId", ""))
                                        platform_str_for_unit = "ios"
                                        # Use user-selected identifier if available
                                        if "ios_ad_unit_identifier" in st.session_state:
                                            android_package_for_unit = st.session_state.ios_ad_unit_identifier.get("value", None)
                                        else:
                                            android_package_for_unit = android_package if android_package else None
                                            # Extract last part if it's a full package name
                                            if android_package_for_unit and '.' in android_package_for_unit:
                                                android_package_for_unit = android_package_for_unit.split('.')[-1]
                                    else:
                                        continue
                                    
                                    # Generate unit names for RV, IS, BN
                                    from components.create_app_helpers import generate_slot_name
                                    
                                    network_manager = get_network_manager()
                                    
                                    unit_names = {}
                                    for slot_type in ["rv", "is", "bn"]:
                                        slot_name = generate_slot_name(
                                            pkg_name, 
                                            platform_str_for_unit, 
                                            slot_type, 
                                            network_key,
                                            bundle_id=bundle_id,
                                            network_manager=network_manager,
                                            app_name=app_name,
                                            android_package_name=android_package_for_unit
                                        )
                                        if slot_name:
                                            unit_names[slot_type.upper()] = slot_name
                                    
                                    if unit_names:
                                        st.markdown("**생성될 Unit 이름:**")
                                        
                                        unit_cols = st.columns(len(unit_names))
                                        for idx, (slot_type, slot_name) in enumerate(unit_names.items()):
                                            with unit_cols[idx]:
                                                st.text_input(
                                                    f"{slot_type} Unit Name",
                                                    value=slot_name,
                                                    key=f"unit_name_{network_key}_{platform_value}_{slot_type}",
                                                    disabled=True
                                                )
                                        
                                        # Create single button to create all units for this platform
                                        if st.button(
                                            f"✅ Create All {platform_display} Units (RV, IS, BN)",
                                            key=f"create_all_units_{network_key}_{platform_value}",
                                            width='stretch',
                                            type="primary"
                                        ):
                                            # Step 1: Deactivate existing placements for this app (Vungle requirement)
                                            try:
                                                with st.spinner(f"Deactivating existing placements for {platform_display}..."):
                                                    existing_placements = network_manager._get_vungle_placements_by_app_id(str(vungle_app_id))
                                                    
                                                    if existing_placements:
                                                        deactivated_count = 0
                                                        for placement in existing_placements:
                                                            # Get placement_id from the placement object first
                                                            initial_placement_id = placement.get("id") or placement.get("placementId")
                                                            if not initial_placement_id:
                                                                logger.warning(f"[Vungle] Placement ID not found in placement object: {placement}")
                                                                continue
                                                            
                                                            try:
                                                                # Use VungleAPI to get placement details first
                                                                if network_manager._vungle_api is None:
                                                                    from utils.network_apis.vungle_api import VungleAPI
                                                                    network_manager._vungle_api = VungleAPI()
                                                                
                                                                # GET /placements/{id} to get full placement details
                                                                get_response = network_manager._vungle_api.get_placement(str(initial_placement_id))
                                                                
                                                                if get_response and (get_response.get('status') == 0 or get_response.get('code') == 0):
                                                                    # Extract id from GET placement response
                                                                    placement_result = get_response.get('result', {})
                                                                    placement_id = placement_result.get("id") or initial_placement_id
                                                                    
                                                                    if placement_id:
                                                                        # Update placement status to inactive
                                                                        update_payload = {
                                                                            "status": "inactive"
                                                                        }
                                                                        
                                                                        update_response = network_manager._vungle_api.update_placement(str(placement_id), update_payload)
                                                                        
                                                                        if update_response and (update_response.get('status') == 0 or update_response.get('code') == 0):
                                                                            deactivated_count += 1
                                                                        else:
                                                                            logger.warning(f"[Vungle] Failed to deactivate placement {placement_id}: {update_response.get('msg', 'Unknown error') if update_response else 'No response'}")
                                                                    else:
                                                                        logger.warning(f"[Vungle] Placement ID not found in GET response: {get_response}")
                                                                else:
                                                                    logger.warning(f"[Vungle] Failed to get placement {initial_placement_id}: {get_response.get('msg', 'Unknown error') if get_response else 'No response'}")
                                                            except Exception as e:
                                                                logger.warning(f"[Vungle] Error getting/deactivating placement {initial_placement_id}: {str(e)}")
                                                        
                                                        if deactivated_count > 0:
                                                            st.info(f"ℹ️ {deactivated_count}개 기존 placements를 inactive로 변경했습니다.")
                                                        else:
                                                            st.info("ℹ️ 기존 placements를 찾을 수 없거나 이미 inactive 상태입니다.")
                                                    else:
                                                        st.info("ℹ️ 기존 placements가 없습니다.")
                                            except Exception as e:
                                                logger.warning(f"[Vungle] Error fetching/deactivating existing placements: {str(e)}")
                                                st.warning(f"⚠️ 기존 placements 조회/비활성화 중 오류 발생: {str(e)}. 계속 진행합니다...")
                                            
                                            success_count = 0
                                            failure_count = 0
                                            
                                            for slot_type, slot_name in unit_names.items():
                                                try:
                                                    # Build payload using config.build_unit_payload
                                                    slot_type_lower = slot_type.lower()
                                                    unit_type_map = {
                                                        "RV": "rewarded",
                                                        "IS": "interstitial",
                                                        "BN": "banner"
                                                    }
                                                    vungle_unit_type = unit_type_map.get(slot_type, slot_type_lower)
                                                    
                                                    form_data = {
                                                        "application": str(vungle_app_id),
                                                        "name": slot_name,
                                                        "type": vungle_unit_type
                                                    }
                                                    
                                                    payload = config.build_unit_payload(form_data)
                                                    
                                                    # Create unit
                                                    with st.spinner(f"Creating {slot_type} ({platform_display})..."):
                                                        response = network_manager.create_unit(network_key, payload)
                                                        
                                                        if response and (response.get('status') == 0 or response.get('code') == 0):
                                                            success_count += 1
                                                            
                                                            # Track unit creation result
                                                            if network_key not in st.session_state.creation_results:
                                                                st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                                            st.session_state.creation_results[network_key]["units"].append({
                                                                "platform": platform_display,
                                                                "app_name": app_name,
                                                                "unit_name": slot_name,
                                                                "unit_type": slot_type,
                                                                "success": True
                                                            })
                                                            
                                                            st.success(f"✅ {slot_type} Unit 생성 완료! ({platform_display})")
                                                        else:
                                                            failure_count += 1
                                                            error_msg = response.get("msg", "Unknown error") if response else "No response"
                                                            
                                                            # Track unit creation failure
                                                            if network_key not in st.session_state.creation_results:
                                                                st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                                            st.session_state.creation_results[network_key]["units"].append({
                                                                "platform": platform_display,
                                                                "app_name": app_name,
                                                                "unit_name": slot_name,
                                                                "unit_type": slot_type,
                                                                "success": False,
                                                                "error": error_msg
                                                            })
                                                            
                                                            st.error(f"❌ {slot_type} Unit 생성 실패 ({platform_display}): {error_msg}")
                                                except Exception as e:
                                                    failure_count += 1
                                                    
                                                    # Track unit creation failure
                                                    if network_key not in st.session_state.creation_results:
                                                        st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                                    st.session_state.creation_results[network_key]["units"].append({
                                                        "platform": platform_display,
                                                        "app_name": app_name,
                                                        "unit_name": slot_name,
                                                        "unit_type": slot_type,
                                                        "success": False,
                                                        "error": str(e)
                                                    })
                                                    
                                                    st.error(f"❌ {slot_type} Unit 생성 실패 ({platform_display}): {str(e)}")
                                                    logger.error(f"Error creating {slot_type} unit for {network_key} ({platform_display}): {str(e)}", exc_info=True)
                                            
                                            # Summary
                                            if success_count == 3:
                                                st.balloons()
                                                st.success(f"🎉 {platform_display} 모든 Unit 생성 완료! (RV, IS, BN)")
                                            elif success_count > 0:
                                                st.warning(f"⚠️ {platform_display} {success_count}/3 Unit 생성 완료, {failure_count}개 실패")
                                            else:
                                                st.error(f"❌ {platform_display} 모든 Unit 생성 실패")
                                    else:
                                        st.warning(f"⚠️ {platform_display}: Unit 이름을 생성할 수 없습니다.")
                                    
                                    st.markdown("---")
                                
                                # Skip the default unit creation logic for Vungle
                                continue
                            
                            # Generate unit names for RV, IS, BN (for other networks)
                            # For multi-platform networks, handle each platform separately
                            from components.create_app_helpers import generate_slot_name
                            
                            network_manager = get_network_manager()
                            
                            # Check if this is a multi-platform network with results
                            if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "mintegral", "pangle"] and app_data.get("results"):
                                # Multi-platform: generate unit names for each platform separately
                                results_list = app_data.get("results", [])
                                preview_info = preview_data.get(network_key, {})
                                mapped_params = preview_info.get("params", {})
                                
                                # Collect unit names by platform
                                unit_names_by_platform = {}
                                for platform, result, response in results_list:
                                    platform_value = platform.lower() if isinstance(platform, str) else "android"
                                    
                                    # Get platform-specific package name/bundle ID from mapped_params
                                    # For InMobi, also try to get from store_info in session state
                                    if platform_value == "android":
                                        pkg_name = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("androidBundle", ""))))
                                        # For InMobi, try to get from store_info_android first, then from androidStoreUrl
                                        if not pkg_name and network_key == "inmobi":
                                            # Try from session state store_info
                                            android_info = st.session_state.get("store_info_android", {})
                                            if android_info:
                                                pkg_name = android_info.get("package_name", "")
                                            # Fallback: extract from androidStoreUrl
                                            if not pkg_name:
                                                android_store_url = mapped_params.get("androidStoreUrl", "")
                                                if android_store_url and "id=" in android_store_url:
                                                    try:
                                                        pkg_name = android_store_url.split("id=")[1].split("&")[0].split("#")[0]
                                                    except:
                                                        pass
                                        bundle_id = ""  # Android uses package name only
                                        platform_str_for_unit = "android"
                                    elif platform_value == "ios":
                                        pkg_name = ""  # iOS uses bundle ID only
                                        bundle_id = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("iosBundle", ""))))
                                        # For InMobi, try to get from store_info_ios first, then from iosStoreUrl
                                        if not bundle_id and network_key == "inmobi":
                                            # Try from session state store_info
                                            ios_info = st.session_state.get("store_info_ios", {})
                                            if ios_info:
                                                bundle_id = ios_info.get("bundle_id", "")
                                            # Fallback: extract from iosStoreUrl
                                            if not bundle_id:
                                                ios_store_url = mapped_params.get("iosStoreUrl", "")
                                                if ios_store_url and "/id" in ios_store_url:
                                                    try:
                                                        # Extract iTunes ID (e.g., id6444113828)
                                                        bundle_id = ios_store_url.rstrip("/").split("/")[-1]
                                                    except:
                                                        pass
                                        platform_str_for_unit = "ios"
                                    else:
                                        continue
                                    
                                    # Generate unit names for this platform
                                    platform_unit_names = {}
                                    for slot_type in ["rv", "is", "bn"]:
                                        slot_name = generate_slot_name(
                                            pkg_name,
                                            platform_str_for_unit,
                                            slot_type,
                                            network_key,
                                            bundle_id=bundle_id,
                                            network_manager=network_manager,
                                            app_name=app_name
                                        )
                                        if slot_name:
                                            platform_unit_names[slot_type.upper()] = slot_name
                                    
                                    if platform_unit_names:
                                        unit_names_by_platform[platform] = platform_unit_names
                                
                                # For display, show both platforms if available, or use first available
                                if len(unit_names_by_platform) > 1:
                                    # Multiple platforms: show Android first, then iOS
                                    unit_names = {}
                                    if "Android" in unit_names_by_platform:
                                        unit_names = unit_names_by_platform["Android"]
                                    elif "android" in unit_names_by_platform:
                                        unit_names = unit_names_by_platform["android"]
                                    else:
                                        unit_names = list(unit_names_by_platform.values())[0]
                                elif len(unit_names_by_platform) == 1:
                                    unit_names = list(unit_names_by_platform.values())[0]
                                else:
                                    unit_names = {}
                            else:
                                # Single platform or fallback: use app_info directly with platform-specific logic
                                platform_str_value = app_info.get("platformStr", "android").lower()
                                
                                # Use platform-specific values: Android -> pkgName, iOS -> bundleId
                                if platform_str_value == "android":
                                    pkg_name = app_info.get("pkgNameDisplay") or app_info.get("pkgName", "")
                                    bundle_id = ""  # Android uses package name only
                                elif platform_str_value == "ios":
                                    pkg_name = ""  # iOS uses bundle ID only
                                    bundle_id = app_info.get("bundleId", "")
                                else:
                                    # Fallback: try both, but prefer pkgName for Android-like, bundleId for iOS-like
                                    pkg_name = app_info.get("pkgNameDisplay") or app_info.get("pkgName", "")
                                    bundle_id = app_info.get("bundleId", "")
                                
                                unit_names = {}
                                for slot_type in ["rv", "is", "bn"]:
                                    slot_name = generate_slot_name(
                                        pkg_name, 
                                        platform_str, 
                                        slot_type, 
                                        network_key,
                                        bundle_id=bundle_id,
                                        network_manager=network_manager,
                                        app_name=app_name
                                    )
                                    if slot_name:
                                        unit_names[slot_type.upper()] = slot_name
                                
                                if unit_names:
                                    st.markdown("##### ✅ Create Ad Units")
                                    st.markdown("**생성될 Unit 이름:**")
                                    
                                    unit_cols = st.columns(len(unit_names))
                                    for idx, (slot_type, slot_name) in enumerate(unit_names.items()):
                                        with unit_cols[idx]:
                                            st.text_input(
                                                f"{slot_type} Unit Name",
                                                value=slot_name,
                                                key=f"unit_name_{network_key}_{slot_type}",
                                                disabled=True
                                            )
                                    
                                    # Create buttons for each unit type
                                    create_unit_cols = st.columns(len(unit_names))
                                    for idx, (slot_type, slot_name) in enumerate(unit_names.items()):
                                        with create_unit_cols[idx]:
                                            if st.button(
                                                f"✅ Create {slot_type}",
                                                key=f"create_unit_{network_key}_{slot_type}",
                                                width='stretch'
                                            ):
                                                # Ensure created_apps_by_network is preserved in session state
                                                if "created_apps_by_network" not in st.session_state:
                                                    st.session_state.created_apps_by_network = created_apps_by_network
                                                else:
                                                    # Merge with existing data
                                                    st.session_state.created_apps_by_network.update(created_apps_by_network)
                                                
                                                try:
                                                    # Build payload and call API directly instead of using create_default_slot
                                                    # to avoid UI rendering issues that cause page reload
                                                    app_code = app_info.get("appCode") or app_info.get("appId") or app_info.get("appKey")
                                                    if not app_code:
                                                        st.error(f"❌ {slot_type} Unit 생성 실패: App Code를 찾을 수 없습니다.")
                                                        logger.error(f"App Code not found for {network_key}: {app_info}")
                                                    else:
                                                        # Build payload based on network
                                                        if network_key == "bigoads":
                                                            payload = {
                                                                "appCode": str(app_code).strip(),
                                                                "name": slot_name,
                                                            }
                                                            if slot_type.lower() == "rv":
                                                                payload.update({"adType": 4, "auctionType": 3, "musicSwitch": 1})
                                                            elif slot_type.lower() == "is":
                                                                payload.update({"adType": 3, "auctionType": 3, "musicSwitch": 1})
                                                            elif slot_type.lower() == "bn":
                                                                payload.update({"adType": 2, "auctionType": 3, "bannerAutoRefresh": 2, "bannerSize": [2]})
                                                        else:
                                                            # For other networks, try to use config.build_unit_payload if available
                                                            if hasattr(config, 'build_unit_payload'):
                                                                payload = config.build_unit_payload({
                                                                    "appCode": str(app_code).strip(),
                                                                    "name": slot_name,
                                                                    "slotType": slot_type.lower()
                                                                })
                                                            else:
                                                                # Fallback: basic payload
                                                                payload = {
                                                                    "appCode": str(app_code).strip(),
                                                                    "name": slot_name,
                                                                }
                                                        
                                                        # Make API call
                                                        with st.spinner(f"Creating {slot_type.upper()} unit..."):
                                                            response = network_manager.create_unit(network_key, payload)
                                                            
                                                            # Check response
                                                            is_success = response.get('status') == 0 or response.get('code') == 0
                                                            
                                                            # Track unit creation result
                                                            platform_str = app_info.get("platformStr", "android")
                                                            platform_display = "Android" if platform_str.lower() == "android" else "iOS"
                                                            if network_key not in st.session_state.creation_results:
                                                                st.session_state.creation_results[network_key] = {"network": platform_display, "apps": [], "units": []}
                                                            st.session_state.creation_results[network_key]["units"].append({
                                                                "platform": platform_display,
                                                                "app_name": app_info.get("name", "Unknown"),
                                                                "unit_name": slot_name,
                                                                "unit_type": slot_type.upper(),
                                                                "success": is_success
                                                            })
                                                            
                                                            if is_success:
                                                                st.success(f"✅ {slot_type} Unit 생성 완료!")
                                                            else:
                                                                error_msg = response.get("msg", "Unknown error") if response else "No response"
                                                                st.error(f"❌ {slot_type} Unit 생성 실패: {error_msg}")
                                                                logger.error(f"Failed to create {slot_type} unit for {network_key}: {error_msg}")
                                                except Exception as e:
                                                    # Track unit creation failure
                                                    platform_str = app_info.get("platformStr", "android")
                                                    platform_display = "Android" if platform_str.lower() == "android" else "iOS"
                                                    if network_key not in st.session_state.creation_results:
                                                        st.session_state.creation_results[network_key] = {"network": network_display, "apps": [], "units": []}
                                                    st.session_state.creation_results[network_key]["units"].append({
                                                        "platform": platform_display,
                                                        "app_name": app_info.get("name", "Unknown"),
                                                        "unit_name": slot_name,
                                                        "unit_type": slot_type.upper(),
                                                        "success": False,
                                                        "error": str(e)
                                                    })
                                                    st.error(f"❌ {slot_type} Unit 생성 실패: {str(e)}")
                                                    logger.error(f"Error creating {slot_type} unit for {network_key}: {str(e)}", exc_info=True)
                                else:
                                    st.warning(f"⚠️ {network_display}: Unit 이름을 생성할 수 없습니다.")
                            
                            st.markdown("---")
                
                # Show Results Summary (팝업 스타일) - 마지막에 표시
                if st.session_state.get("creation_results"):
                    st.divider()
                    st.markdown("### 📊 생성 결과 요약")
                    
                    # Create a modal/popup style summary with expander
                    with st.expander("📋 전체 생성 결과 보기", expanded=True):
                        results = st.session_state.creation_results
                        
                        if results:
                            # Create summary table
                            summary_data = []
                            
                            for network_key, network_data in results.items():
                                network_name = network_data.get("network", network_key)
                                apps = network_data.get("apps", [])
                                units = network_data.get("units", [])
                                
                                # Add app results
                                for app in apps:
                                    summary_data.append({
                                        "네트워크": network_name,
                                        "OS (Platform)": app.get("platform", "N/A"),
                                        "App": app.get("app_name", "N/A"),
                                        "Ad Unit": "-",
                                        "Unit Type": "-",
                                        "성공 여부": "✅ 성공" if app.get("success") else "❌ 실패"
                                    })
                                
                                # Add unit results
                                for unit in units:
                                    success_status = "✅ 성공" if unit.get("success") else f"❌ 실패: {unit.get('error', 'Unknown')}"
                                    summary_data.append({
                                        "네트워크": network_name,
                                        "OS (Platform)": unit.get("platform", "N/A"),
                                        "App": unit.get("app_name", "N/A"),
                                        "Ad Unit": unit.get("unit_name", "N/A"),
                                        "Unit Type": unit.get("unit_type", "N/A"),
                                        "성공 여부": success_status
                                    })
                            
                            if summary_data:
                                import pandas as pd
                                df = pd.DataFrame(summary_data)
                                
                                # Style the dataframe
                                styled_df = df.style.applymap(
                                    lambda x: "background-color: #d4edda; color: #155724" if "✅" in str(x) else "background-color: #f8d7da; color: #721c24" if "❌" in str(x) else "",
                                    subset=["성공 여부"]
                                )
                                
                                st.dataframe(df, width='stretch', hide_index=True)
                                
                                # Summary statistics
                                total_apps = sum(len(r.get("apps", [])) for r in results.values())
                                total_units = sum(len(r.get("units", [])) for r in results.values())
                                successful_apps = sum(sum(1 for app in r.get("apps", []) if app.get("success")) for r in results.values())
                                successful_units = sum(sum(1 for unit in r.get("units", []) if unit.get("success")) for r in results.values())
                                
                                st.markdown("#### 📈 통계")
                                stat_cols = st.columns(4)
                                with stat_cols[0]:
                                    st.metric("총 App 생성", total_apps, f"성공: {successful_apps}")
                                with stat_cols[1]:
                                    st.metric("총 Unit 생성", total_units, f"성공: {successful_units}")
                                with stat_cols[2]:
                                    app_success_rate = (successful_apps / total_apps * 100) if total_apps > 0 else 0
                                    st.metric("App 성공률", f"{app_success_rate:.1f}%")
                                with stat_cols[3]:
                                    unit_success_rate = (successful_units / total_units * 100) if total_units > 0 else 0
                                    st.metric("Unit 성공률", f"{unit_success_rate:.1f}%")
                            else:
                                st.info("생성된 항목이 없습니다.")
                        else:
                            st.info("생성 결과가 없습니다.")

