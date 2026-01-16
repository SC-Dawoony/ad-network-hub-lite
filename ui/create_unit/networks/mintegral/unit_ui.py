"""Mintegral Create Unit UI"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from utils.ui_helpers import handle_api_response
from components.create_app_helpers import (
    normalize_platform_str,
    generate_slot_name
)

logger = logging.getLogger(__name__)


def render_mintegral_slot_ui(slot_key, slot_config, selected_app_code, app_info_to_use,
                              app_name, apps, network_manager, current_network):
    """Render Mintegral slot UI"""
    placement_name_key = f"mintegral_slot_{slot_key}_name"
    
    # Track last selected app code to detect changes
    last_app_code_key = f"mintegral_last_app_code_{slot_key}"
    last_app_code = st.session_state.get(last_app_code_key, "")
    
    # Auto-generate placement name if not set or if app selection changed
    app_selection_changed = selected_app_code and selected_app_code != last_app_code
    should_regenerate = (
        placement_name_key not in st.session_state or 
        app_selection_changed
    )
    
    if selected_app_code and should_regenerate:
        logger.info(f"[Mintegral] Regenerating placement name. selected_app_code: {selected_app_code} (type: {type(selected_app_code).__name__}), last_app_code: {last_app_code}, app_selection_changed: {app_selection_changed}")
        logger.info(f"[Mintegral] apps list length: {len(apps)}, app_info_to_use: {app_info_to_use is not None}")
        pkg_name = ""
        platform_str = "android"
        app_name_for_slot = app_name
        
        if app_info_to_use:
            pkg_name = app_info_to_use.get("pkgName", "")
            platform_str = app_info_to_use.get("platformStr", "android")
            app_name_for_slot = app_info_to_use.get("name", app_name)
            logger.info(f"[Mintegral] From app_info_to_use: name={app_name_for_slot}, pkg={pkg_name}, platform={platform_str}")
        
        # Always try to get from apps list first (more reliable)
        found_in_apps = False
        for app in apps:
            app_identifier = app.get("appCode")
            # Try both string and int comparison
            if str(app_identifier) == str(selected_app_code) or app_identifier == selected_app_code:
                found_in_apps = True
                # Always update from apps list when app selection changes
                if app_selection_changed or not pkg_name:
                    pkg_name = app.get("pkgName", "")
                if app_selection_changed or not platform_str or platform_str == "unknown":
                    platform_from_app = app.get("platform", "")
                    platform_str = normalize_platform_str(platform_from_app, "mintegral")
                if app_selection_changed or not app_name_for_slot or app_name_for_slot == app_name:
                    app_name_for_slot = app.get("name", app_name)
                logger.info(f"[Mintegral] Found app in apps list: name={app_name_for_slot}, pkg={pkg_name}, platform={platform_str}, appCode={app_identifier}")
                break
        
        if not found_in_apps:
            logger.warning(f"[Mintegral] App {selected_app_code} not found in apps list. Available appCodes: {[app.get('appCode') for app in apps[:5]]}")
        
        platform_str = normalize_platform_str(platform_str, "mintegral")
        
        # For iOS apps, if pkg_name is iTunes ID (starts with "id" followed by numbers),
        # try to find Android version of the same app by matching app_name
        if platform_str == "ios" and pkg_name and pkg_name.startswith("id") and pkg_name[2:].isdigit():
            logger.info(f"[Mintegral] iOS app with iTunes ID: {pkg_name}, searching for Android version with app_name: {app_name_for_slot}")
            logger.info(f"[Mintegral] Searching in {len(apps)} apps for Android version")
            # Search for Android app with same app_name in apps list first
            android_found = False
            for app in apps:
                app_platform = app.get("platform", "")
                app_platform_normalized = normalize_platform_str(app_platform, "mintegral")
                app_name_from_list = app.get("name", "")
                
                logger.debug(f"[Mintegral] Checking app: name={app_name_from_list}, platform={app_platform} (normalized: {app_platform_normalized})")
                
                if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                    android_pkg_name = app.get("pkgName", "")
                    if android_pkg_name and not android_pkg_name.startswith("id"):
                        logger.info(f"[Mintegral] Found Android app with same name in apps list, using package: {android_pkg_name}")
                        pkg_name = android_pkg_name
                        android_found = True
                        break
            
            # If not found in apps list, try fetching all apps from API
            if not android_found:
                logger.info(f"[Mintegral] Android app not found in apps list ({len(apps)} apps), fetching all apps from API")
                try:
                    all_apps = network_manager.get_apps(current_network)
                    if all_apps:
                        logger.info(f"[Mintegral] Fetched {len(all_apps)} apps from API, searching for Android version")
                        for app in all_apps:
                            app_platform = app.get("platform", "")
                            app_platform_normalized = normalize_platform_str(app_platform, "mintegral")
                            app_name_from_list = app.get("name", "")
                            
                            if app_platform_normalized == "android" and app_name_from_list == app_name_for_slot:
                                android_pkg_name = app.get("pkgName", "")
                                if android_pkg_name and not android_pkg_name.startswith("id"):
                                    logger.info(f"[Mintegral] Found Android app with same name in full apps list, using package: {android_pkg_name}")
                                    pkg_name = android_pkg_name
                                    android_found = True
                                    break
                except Exception as e:
                    logger.warning(f"[Mintegral] Failed to fetch all apps from API: {str(e)}")
            
            if not android_found:
                logger.warning(f"[Mintegral] Could not find Android app with name '{app_name_for_slot}' in apps list. Available apps: {[(app.get('name'), app.get('platform')) for app in apps]}")
        
        # Generate placement name if we have a valid package name (not iTunes ID)
        logger.info(f"[Mintegral] Before generating: pkg_name={pkg_name}, platform_str={platform_str}, app_name_for_slot={app_name_for_slot}")
        if pkg_name and not (pkg_name.startswith("id") and pkg_name[2:].isdigit()):
            default_name = generate_slot_name(pkg_name, platform_str, slot_key.lower(), "mintegral", network_manager=network_manager, app_name=app_name_for_slot)
            logger.info(f"[Mintegral] Generated placement name: {default_name} for app: {app_name_for_slot}, pkg: {pkg_name}")
            if default_name:
                st.session_state[placement_name_key] = default_name
            else:
                # generate_slot_name returned empty, use fallback
                logger.warning(f"[Mintegral] generate_slot_name returned empty, using fallback")
                default_name = f"{slot_key.lower()}_placement"
                st.session_state[placement_name_key] = default_name
        else:
            # No valid package name found, use fallback
            logger.warning(f"[Mintegral] No valid package name found (pkg_name: {pkg_name}), using fallback")
            default_name = f"{slot_key.lower()}_placement"
            st.session_state[placement_name_key] = default_name
        
        # Update last app code
        st.session_state[last_app_code_key] = selected_app_code
    elif placement_name_key not in st.session_state:
        default_name = f"{slot_key.lower()}_placement"
        st.session_state[placement_name_key] = default_name
    
    placement_name = st.text_input(
        "Placement Name*",
        value=st.session_state[placement_name_key],
        key=placement_name_key,
        help=f"Name for {slot_config['name']} placement"
    )
    
    app_id_key = f"mintegral_slot_{slot_key}_app_id"
    
    # Priority: 1) app_info_to_use, 2) last_app_info, 3) apps list, 4) session_state
    app_id_from_app = None
    
    # First, try to get app_id from app_info_to_use (from selected app)
    if app_info_to_use:
        app_id_from_app = app_info_to_use.get("app_id") or app_info_to_use.get("appId") or app_info_to_use.get("appCode")
        logger.info(f"[Mintegral] app_info_to_use app_id: {app_id_from_app}, keys: {list(app_info_to_use.keys())}")
    
    # If not found, try last_app_info (from Create App response)
    if not app_id_from_app:
        last_app_info = SessionManager.get_last_created_app_info(current_network)
        if last_app_info:
            app_id_from_app = last_app_info.get("app_id") or last_app_info.get("appId") or last_app_info.get("appCode")
            logger.info(f"[Mintegral] last_app_info app_id: {app_id_from_app}, keys: {list(last_app_info.keys()) if last_app_info else []}")
    
    # If still not found, try to get from apps list using selected_app_code
    if not app_id_from_app and selected_app_code:
        for app in apps:
            app_identifier = app.get("appCode") or app.get("app_id") or app.get("appId") or app.get("id")
            if app_identifier == selected_app_code or str(app_identifier) == str(selected_app_code):
                app_id_from_app = app.get("app_id") or app.get("appId") or app.get("id")
                logger.info(f"[Mintegral] Found app_id from apps list: {app_id_from_app}")
                break
    
    # Calculate default_app_id
    if app_id_from_app:
        try:
            default_app_id = max(1, int(app_id_from_app)) if app_id_from_app else 1
            logger.info(f"[Mintegral] Using app_id_from_app: {app_id_from_app} -> default_app_id: {default_app_id}")
        except (ValueError, TypeError) as e:
            logger.warning(f"[Mintegral] Failed to convert app_id_from_app to int: {app_id_from_app}, error: {e}")
            default_app_id = 1
    else:
        # Check session_state, but prefer app_id_from_app if available
        default_app_id = st.session_state.get(app_id_key, 1)
        if default_app_id < 1:
            default_app_id = 1
        logger.info(f"[Mintegral] No app_id found, using session_state: {default_app_id}")
    
    # Only update session_state if we have a valid app_id_from_app
    if app_id_from_app and default_app_id > 1:
        st.session_state[app_id_key] = default_app_id
    
    app_id = st.number_input(
        "App ID*",
        value=default_app_id,
        min_value=1,
        key=app_id_key,
        help="Media ID from created app or enter manually"
    )
    
    st.markdown("**Current Settings:**")
    settings_html = '<div style="min-height: 180px; margin-bottom: 10px;">'
    settings_html += f'<ul style="margin: 0; padding-left: 20px;">'
    settings_html += f'<li>Ad Type: {slot_config["ad_type"].replace("_", " ").title()}</li>'
    settings_html += f'<li>Integration Type: SDK</li>'
    
    if slot_key == "RV":
        skip_time_text = "Non Skippable" if slot_config["skip_time"] == -1 else f"{slot_config['skip_time']} seconds"
        settings_html += f'<li>Skip Time: {skip_time_text}</li>'
        settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    elif slot_key == "IS":
        content_type_text = slot_config.get("content_type", "both").title()
        ad_space_text = "Full Screen Interstitial" if slot_config.get("ad_space_type", 1) == 1 else "Half Screen Interstitial"
        skip_time_text = "Non Skippable" if slot_config["skip_time"] == -1 else f"{slot_config['skip_time']} seconds"
        settings_html += f'<li>Content Type: {content_type_text}</li>'
        settings_html += f'<li>Ad Space Type: {ad_space_text}</li>'
        settings_html += f'<li>Skip Time: {skip_time_text}</li>'
        settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
    elif slot_key == "BN":
        show_close_text = "No" if slot_config.get("show_close_button", 0) == 0 else "Yes"
        auto_fresh_text = "Turn Off" if slot_config.get("auto_fresh", 0) == 0 else "Turn On"
        settings_html += f'<li>Show Close Button: {show_close_text}</li>'
        settings_html += f'<li>Auto Refresh: {auto_fresh_text}</li>'
        settings_html += f'<li>HB Unit Name: {placement_name if placement_name else "(same as Placement Name)"}</li>'
        settings_html += f'<li style="visibility: hidden;">&nbsp;</li>'
    
    settings_html += '</ul></div>'
    st.markdown(settings_html, unsafe_allow_html=True)
    
    with st.expander("⚙️ Edit Settings"):
        if slot_key == "RV":
            skip_time = st.number_input(
                "Skip Time (seconds)",
                min_value=-1,
                max_value=30,
                value=slot_config.get("skip_time", -1),
                key=f"{slot_key}_skip_time",
                help="-1 for non-skippable, 0-30 for skippable"
            )
            slot_config["skip_time"] = skip_time
        elif slot_key == "IS":
            content_type = st.selectbox(
                "Content Type",
                options=[("Image", "image"), ("Video", "video"), ("Both", "both")],
                index=2 if slot_config.get("content_type", "both") == "both" else (0 if slot_config.get("content_type") == "image" else 1),
                key=f"{slot_key}_content_type",
                format_func=lambda x: x[0]
            )
            slot_config["content_type"] = content_type[1]
            
            ad_space_type = st.selectbox(
                "Ad Space Type",
                options=[("Full Screen Interstitial", 1), ("Half Screen Interstitial", 2)],
                index=0 if slot_config.get("ad_space_type", 1) == 1 else 1,
                key=f"{slot_key}_ad_space_type",
                format_func=lambda x: x[0]
            )
            slot_config["ad_space_type"] = ad_space_type[1]
            
            skip_time = st.number_input(
                "Skip Time (seconds)",
                min_value=-1,
                max_value=30,
                value=slot_config.get("skip_time", -1),
                key=f"{slot_key}_skip_time",
                help="-1 for non-skippable, 0-30 for skippable"
            )
            slot_config["skip_time"] = skip_time
        elif slot_key == "BN":
            show_close_button = st.selectbox(
                "Show Close Button",
                options=[("No", 0), ("Yes", 1)],
                index=0 if slot_config.get("show_close_button", 0) == 0 else 1,
                key=f"{slot_key}_show_close_button",
                format_func=lambda x: x[0]
            )
            slot_config["show_close_button"] = show_close_button[1]
            
            auto_fresh = st.selectbox(
                "Auto Refresh",
                options=[("Turn Off", 0), ("Turn On", 1)],
                index=0 if slot_config.get("auto_fresh", 0) == 0 else 1,
                key=f"{slot_key}_auto_fresh",
                format_func=lambda x: x[0]
            )
            slot_config["auto_fresh"] = auto_fresh[1]
    
    if st.button(f"✅ Create {slot_key} Placement", use_container_width=True, key=f"create_mintegral_{slot_key}"):
        if not placement_name:
            st.toast("❌ Placement Name is required", icon="🚫")
        elif not app_id or app_id <= 0:
            st.error(f"❌ App ID is required and must be greater than 0. Current value: {app_id}")
            st.write(f"**Debug Info:**")
            st.write(f"- app_info_to_use: {app_info_to_use}")
            st.write(f"- selected_app_code: {selected_app_code}")
            st.write(f"- last_app_info: {SessionManager.get_last_created_app_info(current_network)}")
        else:
            # Ensure app_id is a valid integer
            try:
                app_id_int = int(app_id)
                if app_id_int <= 0:
                    st.error(f"❌ App ID must be greater than 0. Current value: {app_id_int}")
                    st.stop()
            except (ValueError, TypeError):
                st.error(f"❌ App ID must be a valid integer. Current value: {app_id} (type: {type(app_id)})")
                st.stop()
            
            payload = {
                "app_id": app_id_int,
                "placement_name": placement_name,
                "ad_type": slot_config["ad_type"],
                "integrate_type": slot_config.get("integrate_type", "sdk"),
                "hb_unit_name": placement_name,
            }
            
            if slot_key == "RV":
                payload["skip_time"] = slot_config.get("skip_time", -1)
            elif slot_key == "IS":
                payload["content_type"] = slot_config.get("content_type", "both")
                payload["ad_space_type"] = slot_config.get("ad_space_type", 1)
                payload["skip_time"] = slot_config.get("skip_time", -1)
            elif slot_key == "BN":
                payload["show_close_button"] = slot_config.get("show_close_button", 0)
                payload["auto_fresh"] = slot_config.get("auto_fresh", 0)
            
            # Log payload for debugging
            logger.info(f"[Mintegral] Create Unit Payload: {payload}")
            logger.info(f"[Mintegral] Payload keys: {list(payload.keys())}")
            logger.info(f"[Mintegral] app_id type: {type(payload['app_id'])}, value: {payload['app_id']}")
            logger.info(f"[Mintegral] placement_name: {payload['placement_name']}")
            logger.info(f"[Mintegral] ad_type: {payload['ad_type']}")
            logger.info(f"[Mintegral] integrate_type: {payload['integrate_type']}")
            logger.info(f"[Mintegral] hb_unit_name: {payload['hb_unit_name']}")
            
            with st.spinner(f"Creating {slot_key} placement..."):
                try:
                    from utils.network_manager import get_network_manager
                    network_manager = get_network_manager()
                    response = network_manager.create_unit(current_network, payload)
                    result = handle_api_response(response)
                    
                    if result:
                        unit_data = {
                            "slotCode": result.get("placement_id", result.get("id", "N/A")),
                            "name": placement_name,
                            "appCode": str(app_id),
                            "slotType": slot_config["ad_type"],
                            "adType": slot_config["ad_type"],
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
