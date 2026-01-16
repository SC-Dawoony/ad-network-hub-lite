"""Store URL Input Section - Step 1"""
import streamlit as st
from utils.app_store_helper import get_ios_app_details, get_android_app_details


def render_store_url_input():
    """Render Store URL input section and handle app info fetching
    
    Returns:
        tuple: (ios_info, android_info) - Fetched app information
    """
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
    fetch_info_button = st.button("🔍 앱 정보 조회", type="primary", use_container_width=True)
    
    # Initialize session state
    if "store_info_ios" not in st.session_state:
        st.session_state.store_info_ios = None
    if "store_info_android" not in st.session_state:
        st.session_state.store_info_android = None
    
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
    
    return (
        st.session_state.store_info_ios,
        st.session_state.store_info_android
    )

