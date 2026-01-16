"""Pangle Create Unit UI"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_helpers import handle_api_response
from components.create_app_helpers import generate_slot_name

logger = logging.getLogger(__name__)


def render_pangle_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                          app_name, network_manager, current_network):
    """Render Pangle slot UI"""
    slot_name_key = f"pangle_slot_{slot_key}_name"
    
    if selected_app_code and app_info_to_use:
        pkg_name = app_info_to_use.get("pkgName", "")
        platform_str = app_info_to_use.get("platformStr", "android")
        app_name_for_slot = app_info_to_use.get("name", app_name)
        
        if pkg_name:
            default_name = generate_slot_name(pkg_name, platform_str, slot_key.lower(), "pangle", network_manager=network_manager, app_name=app_name_for_slot)
            if slot_name_key not in st.session_state:
                st.session_state[slot_name_key] = default_name
    elif slot_name_key not in st.session_state:
        default_name = f"slot_{slot_key.lower()}"
        st.session_state[slot_name_key] = default_name
    
    slot_name = st.text_input(
        "Slot Name*",
        value=st.session_state[slot_name_key],
        key=slot_name_key,
        help=f"Name for {slot_config['name']} ad placement"
    )
    
    st.info(f"**API Version:** 1.1.13 (auto-generated)")
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Slot Type: {slot_config["name"]}</li>'
    settings_html += f'<li>Render Type: Template Render</li>'
    
    if slot_key == "BN":
        slide_banner_text = "No" if slot_config["slide_banner"] == 1 else "Yes"
        settings_html += f'<li>Slide Banner: {slide_banner_text}</li>'
        settings_html += f'<li>Size: {slot_config["width"]}x{slot_config["height"]}px</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    elif slot_key == "RV":
        orientation_text = "Vertical" if slot_config["orientation"] == 1 else "Horizontal"
        reward_callback_text = "No Server Callback" if slot_config["reward_is_callback"] == 0 else "Server Callback"
        settings_html += f'<li>Orientation: {orientation_text}</li>'
        settings_html += f'<li>Reward Name: {slot_config.get("reward_name", "Reward")}</li>'
        settings_html += f'<li>Reward Count: {slot_config.get("reward_count", 1)}</li>'
        settings_html += f'<li>Reward Callback: {reward_callback_text}</li>'
    elif slot_key == "IS":
        orientation_text = "Vertical" if slot_config["orientation"] == 1 else "Horizontal"
        settings_html += f'<li>Orientation: {orientation_text}</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        if slot_key == "BN":
            slide_banner = st.selectbox(
                "Slide Banner",
                options=[("No", 1), ("Yes", 2)],
                index=0 if slot_config["slide_banner"] == 1 else 1,
                key=f"{slot_key}_slide_banner",
                format_func=lambda x: x[0]
            )
            slot_config["slide_banner"] = slide_banner[1]
            
            banner_size = st.selectbox(
                "Banner Size",
                options=[("640x100 (320*50)", (640, 100)), ("600x500 (300*250)", (600, 500))],
                index=0 if (slot_config["width"], slot_config["height"]) == (640, 100) else 1,
                key=f"{slot_key}_banner_size",
                format_func=lambda x: x[0]
            )
            slot_config["width"] = banner_size[1][0]
            slot_config["height"] = banner_size[1][1]
        elif slot_key == "RV":
            orientation = st.selectbox(
                "Orientation",
                options=[("Vertical", 1), ("Horizontal", 2)],
                index=0 if slot_config["orientation"] == 1 else 1,
                key=f"{slot_key}_orientation",
                format_func=lambda x: x[0]
            )
            slot_config["orientation"] = orientation[1]
            
            reward_name = st.text_input(
                "Reward Name*",
                value=st.session_state.get(f"{slot_key}_reward_name", slot_config.get("reward_name", "Reward")),
                key=f"{slot_key}_reward_name",
                help="Reward name (1-60 characters)"
            )
            slot_config["reward_name"] = reward_name
            
            reward_count = st.number_input(
                "Reward Count*",
                min_value=0,
                max_value=9007199254740991,
                value=st.session_state.get(f"{slot_key}_reward_count", slot_config.get("reward_count", 1)),
                key=f"{slot_key}_reward_count"
            )
            slot_config["reward_count"] = reward_count
            
            reward_is_callback = st.selectbox(
                "Reward Callback",
                options=[("No Server Callback", 0), ("Server Callback", 1)],
                index=0 if slot_config["reward_is_callback"] == 0 else 1,
                key=f"{slot_key}_reward_is_callback",
                format_func=lambda x: x[0]
            )
            slot_config["reward_is_callback"] = reward_is_callback[1]
            
            if reward_is_callback[1] == 1:
                reward_callback_url = st.text_input(
                    "Reward Callback URL*",
                    value=st.session_state.get(f"{slot_key}_reward_callback_url", ""),
                    key=f"{slot_key}_reward_callback_url",
                    help="Required when server callback is enabled"
                )
                slot_config["reward_callback_url"] = reward_callback_url
        elif slot_key == "IS":
            orientation = st.selectbox(
                "Orientation",
                options=[("Vertical", 1), ("Horizontal", 2)],
                index=0 if slot_config["orientation"] == 1 else 1,
                key=f"{slot_key}_orientation",
                format_func=lambda x: x[0]
            )
            slot_config["orientation"] = orientation[1]
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_pangle_{slot_key}"):
        if not slot_name:
            st.toast("❌ Slot Name is required", icon="🚫")
        elif slot_key == "RV" and (not slot_config.get("reward_name") or slot_config.get("reward_count") is None):
            st.toast("❌ Reward Name and Reward Count are required for Rewarded Video", icon="🚫")
        else:
            payload = {
                "app_id": selected_app_code,
                "ad_placement_type": slot_config["ad_slot_type"],
                "bidding_type": 1,
            }
            
            if slot_key == "BN":
                payload.update({
                    "render_type": slot_config["render_type"],
                    "slide_banner": slot_config["slide_banner"],
                    "width": slot_config["width"],
                    "height": slot_config["height"],
                })
            elif slot_key == "RV":
                payload.update({
                    "render_type": slot_config["render_type"],
                    "orientation": slot_config["orientation"],
                    "reward_name": slot_config.get("reward_name", ""),
                    "reward_count": slot_config.get("reward_count", 1),
                    "reward_is_callback": slot_config["reward_is_callback"],
                })
                if slot_config["reward_is_callback"] == 1 and slot_config.get("reward_callback_url"):
                    payload["reward_callback_url"] = slot_config["reward_callback_url"]
            elif slot_key == "IS":
                payload.update({
                    "render_type": slot_config["render_type"],
                    "orientation": slot_config["orientation"],
                })
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload)
                    result = handle_api_response(response)
                    
                    if result:
                        unit_data = {
                            "slotCode": result.get("code_id", result.get("ad_unit_id", "N/A")),
                            "name": slot_name,
                            "appCode": selected_app_code,
                            "slotType": slot_config["ad_slot_type"],
                            "adType": f"Type {slot_config['ad_slot_type']}",
                            "auctionType": "N/A"
                        }
                        SessionManager.add_created_unit(current_network, unit_data)
                        
                        cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                        if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                            cached_units.append(unit_data)
                            SessionManager.cache_units(current_network, selected_app_code, cached_units)
                        
                        st.success(f"✅ {slot_key} placement created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating {slot_key} placement: {str(e)}")
                    SessionManager.log_error(current_network, str(e))
