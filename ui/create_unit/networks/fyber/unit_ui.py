"""Fyber Create Unit UI"""
import streamlit as st
import logging
import re
from utils.session_manager import SessionManager
from utils.ui_helpers import handle_api_response
from components.create_app_helpers import (
    normalize_platform_str,
    generate_slot_name
)

logger = logging.getLogger(__name__)


def render_fyber_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                         app_name, apps, network_manager, current_network, platform=None):
    """Render Fyber slot UI
    
    Args:
        platform: "android" or "ios" to specify which platform to render (for dual-platform display)
    """
    # Use platform-specific key for placement name if platform is specified
    if platform:
        placement_name_key = f"fyber_slot_{slot_key}_{platform}_name"
    else:
        placement_name_key = f"fyber_slot_{slot_key}_name"
    
    if not selected_app_code:
        manual_code = st.session_state.get("manual_app_code_input", "")
        if manual_code:
            selected_app_code = manual_code.strip()
    
    # Get app_id based on platform
    app_id = None
    if selected_app_code:
        if app_info_to_use:
            if platform == "ios":
                # For iOS, use appIdIOS if available
                app_id = app_info_to_use.get("appIdIOS")
            else:
                # For Android or no platform specified, use appId
                app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
        
        if not app_id:
            for app in apps:
                app_identifier = app.get("appId") or app.get("appCode")
                if str(app_identifier) == str(selected_app_code):
                    app_id = app.get("appId") or app.get("app_id")
                    if not app_id:
                        try:
                            app_id = int(app_identifier)
                        except (ValueError, TypeError):
                            app_id = None
                    break
        
        if not app_id:
            try:
                app_id = int(selected_app_code)
            except (ValueError, TypeError):
                numeric_match = re.search(r'\d+', str(selected_app_code))
                if numeric_match:
                    app_id = int(numeric_match.group())
                else:
                    app_id = None
    
    # Auto-generate placement name if not set or if app info is available
    if placement_name_key not in st.session_state or (selected_app_code and app_info_to_use):
        if selected_app_code and app_info_to_use:
            # Get bundle_id and platform_str based on platform
            if platform == "ios":
                # For iOS, try to get iOS-specific bundle
                bundle_id = app_info_to_use.get("iosBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                platform_str = "ios"
            else:
                # For Android or no platform specified
                bundle_id = app_info_to_use.get("androidBundle") or app_info_to_use.get("bundleId") or app_info_to_use.get("bundle") or app_info_to_use.get("pkgName", "")
                platform_str = "android"
            
            pkg_name = app_info_to_use.get("pkgName", "")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            
            source_pkg = bundle_id if bundle_id else pkg_name
            
            if source_pkg:
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                default_name = generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                st.session_state[placement_name_key] = default_name
        elif selected_app_code and app_id:
            # If app_id is available but app_info_to_use is not, try to get bundleId from apps list
            bundle_id = ""
            pkg_name = ""
            platform_str = "android"
            app_name_for_slot = app_name
            
            for app in apps:
                app_identifier = app.get("appId") or app.get("appCode") or app.get("id")
                if str(app_identifier) == str(selected_app_code) or str(app_identifier) == str(app_id):
                    bundle_id = app.get("bundleId") or app.get("bundle", "")
                    pkg_name = app.get("pkgName", "")
                    platform_from_app = app.get("platform", "")
                    platform_str = normalize_platform_str(platform_from_app, "fyber")
                    app_name_for_slot = app.get("name", app_name)
                    break
            
            source_pkg = bundle_id if bundle_id else pkg_name
            
            if source_pkg:
                slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
                slot_type = slot_type_map.get(slot_key, slot_key.lower())
                default_name = generate_slot_name(source_pkg, platform_str, slot_type, "fyber", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
                st.session_state[placement_name_key] = default_name
            else:
                default_name = f"{slot_key.lower()}_placement"
                st.session_state[placement_name_key] = default_name
        else:
            default_name = f"{slot_key.lower()}_placement"
            st.session_state[placement_name_key] = default_name
    
    placement_name = st.text_input(
        "Placement Name*",
        value=st.session_state.get(placement_name_key, ""),
        key=placement_name_key,
        help=f"Name for {slot_config['name']} placement"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 80px; margin-bottom: 10px;">'
    settings_html += '<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Placement Type: {slot_config["placementType"]}</li>'
    settings_html += f'<li>COPPA: {"No" if not slot_config["coppa"] else "Yes"}</li>'
    # Add skipability display for Interstitial
    if slot_key == "IS" and slot_config.get("skipability"):
        settings_html += f'<li>Skipability: {slot_config["skipability"]}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if app_id:
        platform_display = "iOS" if platform == "ios" else "Android" if platform else ""
        if platform_display:
            st.info(f"📱 {platform_display} App ID: {app_id}")
        else:
            st.info(f"📱 App ID: {app_id}")
    elif selected_app_code:
        st.warning(f"⚠️ App ID not found. Will use entered code: {selected_app_code}")
    
    button_key = f"create_fyber_{slot_key}_{platform}" if platform else f"create_fyber_{slot_key}"
    button_label = f"✅ Create {slot_key} Placement ({platform.upper()})" if platform else f"✅ Create {slot_key} Placement"
    if st.button(button_label, use_container_width=True, key=button_key):
        current_app_code = selected_app_code
        if not current_app_code:
            manual_code = st.session_state.get("manual_app_code_input", "")
            if manual_code:
                current_app_code = manual_code.strip()
        
        if not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        elif not current_app_code:
            st.toast("❌ App Code is required. Please select an app or enter manually.", icon="🚫")
        else:
            if not selected_app_code:
                selected_app_code = current_app_code
            
            code_to_parse = current_app_code if current_app_code else selected_app_code
            if not app_id or app_id <= 0:
                try:
                    app_id = int(code_to_parse)
                except (ValueError, TypeError):
                    numeric_match = re.search(r'\d+', str(code_to_parse))
                    if numeric_match:
                        app_id = int(numeric_match.group())
                    else:
                        app_id = None
                        st.toast("❌ Invalid App ID. Please enter a valid numeric App ID.", icon="🚫")
            
            if not app_id or app_id <= 0:
                st.toast("❌ App ID is required. Please select an app or enter a valid App ID.", icon="🚫")
            else:
                payload = {
                    "name": placement_name.strip(),
                    "appId": str(app_id),
                    "placementType": slot_config["placementType"],
                    "coppa": bool(slot_config["coppa"]),
                }
                
                # Add skipability for Interstitial placement (default: NonSkippable)
                if slot_key == "IS" and slot_config.get("skipability"):
                    payload["skipability"] = slot_config["skipability"]
                
                import json as json_module
                logger.info(f"[Fyber] Creating placement - selected_app_code: {selected_app_code}, appId: {app_id}, payload: {json_module.dumps(payload)}")
                
                with st.spinner(f"Creating {slot_key} placement..."):
                    try:
                        from utils.network_manager import get_network_manager
                        network_manager = get_network_manager()
                        response = network_manager.create_unit(current_network, payload)
                        result = handle_api_response(response)
                        
                        if result:
                            unit_data = {
                                "slotCode": result.get("id", result.get("placementId", "N/A")),
                                "name": placement_name,
                                "appCode": str(app_id),
                                "slotType": slot_config["placementType"],
                                "adType": slot_config["placementType"],
                                "auctionType": "N/A"
                            }
                            SessionManager.add_created_unit(current_network, unit_data)
                            
                            cached_units = SessionManager.get_cached_units(current_network, str(app_id))
                            if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                                cached_units.append(unit_data)
                                SessionManager.cache_units(current_network, str(app_id), cached_units)
                            
                            if st.button("🔄 Refresh Page", key=f"refresh_after_{slot_key}", use_container_width=True):
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                        SessionManager.log_error(current_network, str(e))
