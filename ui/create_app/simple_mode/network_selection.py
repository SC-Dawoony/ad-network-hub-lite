"""Network Selection Section"""
import streamlit as st
from network_configs import get_network_display_names, NETWORK_REGISTRY


def render_network_selection():
    """Render network selection section
    
    Returns:
        list: Selected network keys
    """
    st.markdown("### 2️⃣ 네트워크 선택")
    st.markdown("앱을 생성할 네트워크를 선택하세요 (여러 개 선택 가능)")
    
    # Initialize session state
    if "selected_networks" not in st.session_state:
        st.session_state.selected_networks = []
    
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
        if st.button("✅ 모두 선택", key="select_all_networks", use_container_width=True):
            # Select all networks
            enabled_networks = list(available_networks.keys())
            st.session_state.selected_networks = enabled_networks
            # Update individual checkbox states
            for network_key in enabled_networks:
                st.session_state[f"network_checkbox_{network_key}"] = True
            st.rerun()
    
    with button_cols[1]:
        if st.button("❌ 선택 해제", key="deselect_all_networks", use_container_width=True):
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
    
    return selected_networks, available_networks

