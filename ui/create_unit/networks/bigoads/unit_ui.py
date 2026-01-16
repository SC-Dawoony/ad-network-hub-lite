"""BigOAds Create Unit UI"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_helpers import handle_api_response
from components.create_app_helpers import generate_slot_name

logger = logging.getLogger(__name__)

# Value mappings for display
AD_TYPE_MAP = {
    1: "Native",
    2: "Banner",
    3: "Interstitial",
    4: "Reward Video",
    12: "Splash Ad",
    20: "Pop Up"
}

AUCTION_TYPE_MAP = {
    1: "Waterfall",
    2: "Client Bidding",
    3: "Server Bidding"
}

MUSIC_SWITCH_MAP = {
    1: "Sound On",
    2: "Sound Off"
}

AUTO_REFRESH_MAP = {
    1: "Yes",
    2: "No"
}

BANNER_SIZE_MAP = {
    1: "300x250",
    2: "320x50"
}

# Reverse maps for getting values from display
AD_TYPE_REVERSE = {v: k for k, v in AD_TYPE_MAP.items()}
AUCTION_TYPE_REVERSE = {v: k for k, v in AUCTION_TYPE_MAP.items()}
MUSIC_SWITCH_REVERSE = {v: k for k, v in MUSIC_SWITCH_MAP.items()}
AUTO_REFRESH_REVERSE = {v: k for k, v in AUTO_REFRESH_MAP.items()}
BANNER_SIZE_REVERSE = {v: k for k, v in BANNER_SIZE_MAP.items()}


def render_bigoads_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                            app_name, apps, network_manager, current_network):
    """Render BigOAds slot UI"""
    slot_name_key = f"custom_slot_{slot_key}_name"
    
    pkg_name = ""
    platform_str = "android"
    
    if selected_app_code and app_info_to_use:
        if current_network == "bigoads":
            pkg_name = app_info_to_use.get("pkgNameDisplay", app_info_to_use.get("pkgName", ""))
        else:
            pkg_name = app_info_to_use.get("pkgName", "")
        platform_str = app_info_to_use.get("platformStr", "android")
    elif selected_app_code:
        for app in apps:
            if current_network == "ironsource":
                app_identifier = app.get("appKey") or app.get("appCode")
            else:
                app_identifier = app.get("appCode")
            
            if app_identifier == selected_app_code:
                if current_network == "bigoads":
                    pkg_name = app.get("pkgNameDisplay", app.get("pkgName", ""))
                else:
                    pkg_name = app.get("pkgName", "")
                platform_str_val = app.get("platform", "")
                platform_str = "android" if platform_str_val == "Android" else ("ios" if platform_str_val == "iOS" else "android")
                break
    
    if selected_app_code and pkg_name:
        bundle_id = app_info_to_use.get("bundleId", "") if app_info_to_use else ""
        app_name_for_slot = app_info_to_use.get("name", app_name) if app_info_to_use else app_name
        default_name = generate_slot_name(pkg_name, platform_str, slot_key.lower(), current_network, bundle_id=bundle_id, network_manager=network_manager, app_name=app_name_for_slot)
        st.session_state[slot_name_key] = default_name
    elif slot_name_key not in st.session_state:
        default_name = f"slot_{slot_key.lower()}"
        st.session_state[slot_name_key] = default_name
    
    slot_name = st.text_input(
        "Slot Name*",
        value=st.session_state[slot_name_key],
        key=slot_name_key,
        help=f"Name for {slot_config['name']} slot"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 120px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Type: {AD_TYPE_MAP[slot_config["adType"]]}</li>'
    settings_html += f'<li>Auction Type: {AUCTION_TYPE_MAP[slot_config["auctionType"]]}</li>'
    
    if slot_key == "BN":
        # Get bannerAutoRefresh, fallback to autoRefresh for backward compatibility
        banner_auto_refresh = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
        settings_html += f'<li>Auto Refresh: {AUTO_REFRESH_MAP.get(banner_auto_refresh, "No")}</li>'
        banner_size_w = slot_config.get('bannerSizeW', 250)
        banner_size_h = slot_config.get('bannerSizeH', 320)
        settings_html += f'<li>Banner Size: {banner_size_w}x{banner_size_h}</li>'
    else:
        settings_html += f'<li>Music: {MUSIC_SWITCH_MAP[slot_config["musicSwitch"]]}</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        st.selectbox(
            "Ad Type",
            options=[AD_TYPE_MAP[slot_config['adType']]],
            key=f"{slot_key}_adType_display",
            disabled=True
        )
        
        auction_type_display = AUCTION_TYPE_MAP[slot_config['auctionType']]
        new_auction_type = st.selectbox(
            "Auction Type",
            options=list(AUCTION_TYPE_MAP.values()),
            index=list(AUCTION_TYPE_MAP.values()).index(auction_type_display),
            key=f"{slot_key}_auctionType"
        )
        slot_config['auctionType'] = AUCTION_TYPE_REVERSE[new_auction_type]
        
        if slot_key == "BN":
            # Get bannerAutoRefresh, fallback to autoRefresh for backward compatibility
            current_auto_refresh = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
            auto_refresh_display = AUTO_REFRESH_MAP.get(current_auto_refresh, "No")
            new_auto_refresh = st.selectbox(
                "Auto Refresh",
                options=list(AUTO_REFRESH_MAP.values()),
                index=list(AUTO_REFRESH_MAP.values()).index(auto_refresh_display) if auto_refresh_display in AUTO_REFRESH_MAP.values() else 0,
                key=f"{slot_key}_autoRefresh"
            )
            auto_refresh_value = AUTO_REFRESH_REVERSE[new_auto_refresh]
            slot_config['autoRefresh'] = auto_refresh_value  # Keep for backward compatibility
            slot_config['bannerAutoRefresh'] = auto_refresh_value  # Set bannerAutoRefresh for API
            
            # Banner size is now fixed: 250x320 (bannerSizeMode=2, bannerSizeW=250, bannerSizeH=320)
            # Display current banner size
            banner_size_w = slot_config.get('bannerSizeW', 250)
            banner_size_h = slot_config.get('bannerSizeH', 320)
            st.info(f"Banner Size: {banner_size_w}x{banner_size_h} (Fixed)")
            # Keep values in slot_config
            slot_config['bannerSizeMode'] = slot_config.get('bannerSizeMode', 2)
            slot_config['bannerSizeW'] = banner_size_w
            slot_config['bannerSizeH'] = banner_size_h
        else:
            music_display = MUSIC_SWITCH_MAP[slot_config['musicSwitch']]
            new_music = st.selectbox(
                "Music",
                options=list(MUSIC_SWITCH_MAP.values()),
                index=list(MUSIC_SWITCH_MAP.values()).index(music_display),
                key=f"{slot_key}_musicSwitch"
            )
            slot_config['musicSwitch'] = MUSIC_SWITCH_REVERSE[new_music]
    
    if st.button(f"✅ Create {slot_key} Slot", use_container_width=True, key=f"create_{slot_key}"):
        # Log selected_app_code and slot_name for debugging
        logger.info(f"[BigOAds] Creating {slot_key} slot with appCode: {selected_app_code}, name: {slot_name}")
        logger.info(f"[BigOAds] selected_app_code type: {type(selected_app_code)}, value: {selected_app_code}")
        logger.info(f"[BigOAds] slot_name type: {type(slot_name)}, value: {slot_name}")
        
        # Validate appCode
        if not selected_app_code or (isinstance(selected_app_code, str) and not selected_app_code.strip()):
            st.error("❌ App Code is required. Please select an app or enter manually.")
            logger.error(f"[BigOAds] Invalid appCode: '{selected_app_code}'")
            return
        
        # Validate slot name
        if not slot_name or (isinstance(slot_name, str) and not slot_name.strip()):
            st.error("❌ Slot Name is required. Please enter a slot name.")
            logger.error(f"[BigOAds] Invalid slot_name: '{slot_name}'")
            return
        
        # Ensure appCode and name are strings (not None)
        app_code_str = str(selected_app_code).strip()
        slot_name_str = str(slot_name).strip()
        
        payload = {
            "appCode": app_code_str,
            "name": slot_name_str,
            "adType": slot_config['adType'],
            "auctionType": slot_config['auctionType'],
        }
        
        if slot_key == "BN":
            payload["bannerAutoRefresh"] = slot_config.get('bannerAutoRefresh', slot_config.get('autoRefresh', 2))
            # API requires bannerSize field as array - always set to [2]
            payload["bannerSize"] = [2]
        else:
            payload["musicSwitch"] = slot_config['musicSwitch']
        
        # Log and display final payload
        logger.info(f"[BigOAds] Final payload: {payload}")
        st.markdown("#### 📤 Request Payload")
        st.json(payload)
        
        with st.spinner(f"Creating {slot_key} slot..."):
            try:
                from utils.network_manager import get_network_manager
                network_manager = get_network_manager()
                response = network_manager.create_unit(current_network, payload)
                
                # Display full response
                st.markdown("#### 📥 Response")
                st.json(response)
                
                result = handle_api_response(response)
            
                if result:
                    unit_data = {
                        "slotCode": result.get("slotCode", "N/A"),
                        "name": slot_name,
                        "appCode": selected_app_code,
                        "slotType": slot_key,
                        "adType": slot_config.get('adType', slot_key),
                        "auctionType": slot_config.get('auctionType', "N/A")
                    }
                    SessionManager.add_created_unit(current_network, unit_data)
                    
                    cached_units = SessionManager.get_cached_units(current_network, selected_app_code)
                    if not any(unit.get("slotCode") == unit_data["slotCode"] for unit in cached_units):
                        cached_units.append(unit_data)
                        SessionManager.cache_units(current_network, selected_app_code, cached_units)
                    
                    st.success(f"✅ {slot_key} slot created successfully!")
                    # Don't rerun - keep the response visible
                else:
                    st.error(f"❌ Failed to create {slot_key} slot. Check response above.")
            except Exception as e:
                st.error(f"❌ Error creating {slot_key} slot: {str(e)}")
                SessionManager.log_error(current_network, str(e))
                import traceback
                st.code(traceback.format_exc())
