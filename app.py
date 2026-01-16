"""Main Streamlit app - Ad Network Management Hub"""
import streamlit as st
import os
from typing import Optional
from pathlib import Path
from utils.session_manager import SessionManager
from utils.network_manager import get_network_manager
from network_configs import get_available_networks, get_network_display_names, get_network_config
from utils.helpers import get_env_var



def switch_to_page(page_filename: str):
    """Switch to a page"""
    # Streamlit expects path relative to main script
    # Try different path formats
    page_paths = [
        f"pages/{page_filename}",  # Standard format
        page_filename,  # Just filename (Streamlit auto-detects pages/)
    ]
    
    for page_path in page_paths:
        if Path(page_path).exists():
            try:
                st.switch_page(page_path)
                return
            except Exception as e:
                continue
    
    # If all attempts fail, show error
    st.error(f"Could not navigate to page: {page_filename}. Please use the sidebar navigation.")

# Page configuration
st.set_page_config(
    page_title="Ad Network Management Hub",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
SessionManager.initialize()

# Sidebar - Network Selection
with st.sidebar:
    st.title("🌐 Ad Network Hub")
    st.divider()
    
    # Network selector
    available_networks = get_available_networks()
    display_names = get_network_display_names()
    
    network_options = [display_names.get(n, n.title()) for n in available_networks]
    current_network_display = display_names.get(SessionManager.get_current_network(), SessionManager.get_current_network().title())
    
    selected_network_display = st.selectbox(
        "Active Network",
        options=network_options,
        index=network_options.index(current_network_display) if current_network_display in network_options else 0
    )
    
    # Find network key from display name
    selected_network = None
    for key, display in display_names.items():
        if display == selected_network_display:
            selected_network = key
            break
    
    if selected_network and selected_network != SessionManager.get_current_network():
        SessionManager.switch_network(selected_network)
        st.rerun()
    
    st.divider()
    
    # Quick actions
    st.subheader("Quick Actions")
    
    if st.button("🎯 Create Unit", use_container_width=True):
        switch_to_page(".hidden_Create_Unit.py")
    
    if st.button("⚙️ Update Ad Unit", use_container_width=True):
        switch_to_page("4_Update_Ad_Unit.py")
    
    st.divider()
    
    # Connection status
    st.subheader("Connection Status")
    network_manager = get_network_manager()
    
    for network in available_networks:
        config = get_network_config(network)
        display_name = display_names.get(network, network.title())
        
        # Helper function to get env vars from Streamlit secrets or .env
        def get_env(key: str) -> Optional[str]:
            return get_env_var(key)
        
        # Check if network credentials are set
        if network == "ironsource":
            # Check IronSource credentials
            bearer_token = get_env("IRONSOURCE_BEARER_TOKEN") or get_env("IRONSOURCE_API_TOKEN")
            refresh_token = get_env("IRONSOURCE_REFRESH_TOKEN")
            secret_key = get_env("IRONSOURCE_SECRET_KEY")
            if bearer_token or (refresh_token and secret_key):
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "pangle":
            # Check Pangle credentials
            security_key = get_env("PANGLE_SECURITY_KEY")
            user_id = get_env("PANGLE_USER_ID")
            role_id = get_env("PANGLE_ROLE_ID")
            if security_key and user_id and role_id:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "bigoads":
            # Check for BigOAds credentials
            developer_id = get_env("BIGOADS_DEVELOPER_ID")
            token = get_env("BIGOADS_TOKEN")
            if developer_id and token:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "mintegral":
            # Check for Mintegral credentials
            skey = get_env("MINTEGRAL_SKEY")
            secret = get_env("MINTEGRAL_SECRET")
            if skey and secret:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "inmobi":
            # Check for InMobi credentials
            account_name = get_env("INMOBI_ACCOUNT_NAME")
            account_id = get_env("INMOBI_ACCOUNT_ID")
            username = get_env("INMOBI_USERNAME")
            client_secret = get_env("INMOBI_CLIENT_SECRET")
            # InMobi 인증 방식에 따라 필요한 필드 확인 (API 문서 참조 필요)
            if account_name and account_id and username and client_secret:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "fyber":
            # Check for Fyber (DT) credentials
            client_id = get_env("DT_CLIENT_ID")
            client_secret = get_env("DT_CLIENT_SECRET")
            access_token = get_env("FYBER_ACCESS_TOKEN")
            publisher_id = get_env("FYBER_PUBLISHER_ID")
            # Fyber 인증 방식에 따라 필요한 필드 확인 (API 문서 참조 필요)
            if client_id and client_secret and access_token and publisher_id:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        elif network == "applovin":
            # Check for AppLovin credentials
            api_key = get_env("APPLOVIN_API_KEY")
            if api_key:
                status = "✅ Active"
            else:
                status = "⚠️ Not Set"
        else:
            # For other networks, check credentials
            status = "⚠️ Not Set"
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{display_name}**")
        with col2:
            st.write(status)

# Main content
st.title("🌐 Ad Network Management Hub")
st.markdown("Manage multiple ad networks from a single interface")

# Current network info
current_network = SessionManager.get_current_network()
config = get_network_config(current_network)
display_name = display_names.get(current_network, current_network.title())

st.info(f"**Current Network:** {display_name}")

# Quick Links Section
st.subheader("🚀 Quick Actions")
st.markdown("자주 사용하는 기능에 빠르게 접근하세요.")

quick_cols = st.columns(3)

with quick_cols[0]:
    if st.button("📱 앱 스토어 정보 조회", use_container_width=True, type="primary"):
        switch_to_page("0_App_Store_Info.py")
    st.caption("App Store / Google Play 정보를 조회합니다")

with quick_cols[1]:
    if st.button("🚀 Create App (Simple)", use_container_width=True, type="primary"):
        switch_to_page("2_Create_App_Simple.py")
    st.caption("여러 네트워크에 한 번에 앱을 생성합니다")

with quick_cols[2]:
    if st.button("⚙️ Update Ad Unit", use_container_width=True, type="primary"):
        switch_to_page("4_Update_Ad_Unit.py")
    st.caption("기존 Ad Unit 설정을 업데이트합니다")

st.divider()

# Recent Activity Section (Enhanced)
st.subheader("📝 Recent Activity")
st.markdown("최근에 생성한 앱과 유닛을 확인하세요.")

# Combine data from both sources (Standard Create App & Simple Create App)
from datetime import datetime

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📱 Created Apps")
    
    # From SessionManager (old Create App UI)
    session_apps = st.session_state.get('created_apps', [])
    
    # From creation_results (Create App Simple)
    creation_results = st.session_state.get('creation_results', {})
    
    # Combine all apps
    all_created_apps = []
    
    for app in session_apps:
        all_created_apps.append({
            'name': app.get('name', 'Unknown'),
            'network': app.get('network', 'unknown'),
            'timestamp': app.get('timestamp', ''),
            'source': 'Create App (Standard)',
            'platform': app.get('platform', ''),
            'app_code': app.get('appCode', '')
        })
    
    for network_key, results in creation_results.items():
        network_display = results.get('network', network_key)
        for app in results.get('apps', []):
            if app.get('success', False):
                all_created_apps.append({
                    'name': app.get('app_name', 'Unknown'),
                    'network': network_display,
                    'platform': app.get('platform', ''),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Create App (Simple)',
                    'app_code': None
                })
    
    # Sort by timestamp (most recent first) and show last 10
    if all_created_apps:
        all_created_apps.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        for app in all_created_apps[:10]:
            platform_info = f" ({app.get('platform', '')})" if app.get('platform') else ""
            network_badge = f"`{app.get('network', 'unknown')}`"
            st.markdown(f"- **{app.get('name', 'Unknown')}**{platform_info} - {network_badge}")
    else:
        st.info("No apps created yet")
        st.caption("Create App (Simple) 페이지에서 앱을 생성해보세요.")

with col2:
    st.markdown("#### 🎯 Created Units")
    
    # From SessionManager (old Create Unit UI)
    session_units = st.session_state.get('created_units', [])
    
    # From creation_results (Create App Simple)
    creation_results = st.session_state.get('creation_results', {})
    
    # Combine all units
    all_created_units = []
    
    for unit in session_units:
        all_created_units.append({
            'name': unit.get('name', 'Unknown'),
            'network': unit.get('network', 'unknown'),
            'timestamp': unit.get('timestamp', ''),
            'source': 'Create Unit (Standard)',
            'platform': unit.get('platform', ''),
            'unit_type': unit.get('unit_type', '')
        })
    
    for network_key, results in creation_results.items():
        network_display = results.get('network', network_key)
        for unit in results.get('units', []):
            if unit.get('success', False):
                all_created_units.append({
                    'name': unit.get('unit_name', 'Unknown'),
                    'network': network_display,
                    'platform': unit.get('platform', ''),
                    'unit_type': unit.get('unit_type', ''),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Create App (Simple)'
                })
    
    # Sort by timestamp and show last 10
    if all_created_units:
        all_created_units.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        for unit in all_created_units[:10]:
            platform_info = f" ({unit.get('platform', '')})" if unit.get('platform') else ""
            unit_type_info = f" [{unit.get('unit_type', '')}]" if unit.get('unit_type') else ""
            network_badge = f"`{unit.get('network', 'unknown')}`"
            st.markdown(f"- **{unit.get('name', 'Unknown')}**{platform_info}{unit_type_info} - {network_badge}")
    else:
        st.info("No units created yet")
        st.caption("Create App (Simple) 또는 Create Unit 페이지에서 유닛을 생성해보세요.")

# Settings section
with st.expander("⚙️ Settings"):
    st.write("**Network Credentials**")
    st.info("Configure network API credentials in environment variables or settings file")
    
    st.write("**Export/Import**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export All Data"):
            st.info("Export functionality coming soon")
    with col2:
        if st.button("📤 Import Data"):
            st.info("Import functionality coming soon")
