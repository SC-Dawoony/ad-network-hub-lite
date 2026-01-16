"""InMobi Create Unit UI"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_helpers import handle_api_response
from components.create_app_helpers import (
    normalize_platform_str,
    generate_slot_name
)

logger = logging.getLogger(__name__)


def render_inmobi_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                          app_name, apps, network_manager, current_network):
    """Render InMobi slot UI"""
    placement_name_key = f"inmobi_slot_{slot_key}_name"
    
    app_id = None
    if selected_app_code:
        if app_info_to_use:
            app_id = app_info_to_use.get("app_id") or app_info_to_use.get("appId")
        
        if not app_id:
            try:
                app_id = int(selected_app_code)
            except (ValueError, TypeError):
                app_id = None
        
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
    
    if selected_app_code:
        bundle_id = ""
        pkg_name = ""
        platform_str = "android"
        app_name_for_slot = app_name
        
        for app in apps:
            app_identifier = app.get("appId") or app.get("appCode")
            if str(app_identifier) == str(selected_app_code):
                bundle_id = app.get("bundleId", "")
                pkg_name = app.get("pkgName", "")
                platform_from_app = app.get("platform", "")
                platform_str = normalize_platform_str(platform_from_app, "inmobi")
                app_name_for_slot = app.get("name", app_name)
                break
        
        if (not bundle_id and not pkg_name) or not platform_str or platform_str == "unknown":
            if app_info_to_use:
                if not bundle_id:
                    bundle_id = app_info_to_use.get("bundleId", "")
                if not pkg_name:
                    pkg_name = app_info_to_use.get("pkgName", "")
                if not platform_str or platform_str == "unknown":
                    platform_str_from_info = app_info_to_use.get("platformStr", "android")
                    platform_str = normalize_platform_str(platform_str_from_info, "inmobi")
                if not app_name_for_slot or app_name_for_slot == app_name:
                    app_name_for_slot = app_info_to_use.get("name", app_name)
        
        platform_str = normalize_platform_str(platform_str, "inmobi")
        source_pkg = bundle_id if bundle_id else pkg_name
        
        if source_pkg:
            slot_type_map = {"RV": "rv", "IS": "is", "BN": "bn"}
            slot_type = slot_type_map.get(slot_key, slot_key.lower())
            default_name = generate_slot_name(source_pkg, platform_str, slot_type, "inmobi", bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
            st.session_state[placement_name_key] = default_name
    elif placement_name_key not in st.session_state:
        default_name = f"{slot_key.lower()}-placement-1"
        st.session_state[placement_name_key] = default_name
    
    placement_name = st.text_input(
        "Placement Name*",
        value=st.session_state[placement_name_key],
        key=placement_name_key,
        help=f"Name for {slot_config['name']} placement"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Placement Type: {slot_config["placementType"].replace("_", " ").title()}</li>'
    settings_html += f'<li>Audience Bidding: {"Enabled" if slot_config["isAudienceBiddingEnabled"] else "Disabled"}</li>'
    if slot_config["isAudienceBiddingEnabled"]:
        settings_html += f'<li>Audience Bidding Partner: {slot_config["audienceBiddingPartner"]}</li>'
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_inmobi_{slot_key}"):
        if not selected_app_code:
            st.toast("❌ Please select an App Code", icon="🚫")
        elif not app_id or app_id <= 0:
            st.toast("❌ App ID is required. Please select an App Code.", icon="🚫")
        elif not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        else:
            payload = {
                "appId": int(app_id),
                "placementName": placement_name,
                "placementType": slot_config["placementType"],
                "isAudienceBiddingEnabled": slot_config["isAudienceBiddingEnabled"],
            }
            
            if slot_config["isAudienceBiddingEnabled"]:
                payload["audienceBiddingPartner"] = slot_config["audienceBiddingPartner"]
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload)
                    result = handle_api_response(response)
                    
                    if result:
                        unit_data = {
                            "slotCode": result.get("placementId", result.get("id", "N/A")),
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
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))
