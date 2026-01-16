"""Unit Creation Service - Business logic for ad unit creation"""
import json
import logging
from typing import Dict, List, Optional, Any
import streamlit as st
from services.app_creation import extract_app_info_from_response

logger = logging.getLogger(__name__)


def create_ad_units_immediately(
    network_key: str,
    network_display: str,
    app_response: dict,
    mapped_params: dict,
    platform: str,
    config,
    network_manager,
    app_name: str
) -> List[Dict]:
    """Create ad units immediately after app creation success
    Automatically deactivates existing ad units before creating new ones.
    
    Note: This function has Streamlit UI dependencies (st.spinner, st.success, st.warning, st.session_state).
    Future refactoring should separate UI logic from business logic.
    
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

