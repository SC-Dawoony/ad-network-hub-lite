"""App Info Display Section"""
import streamlit as st


def render_app_info_display():
    """Render fetched app information display section"""
    if not (st.session_state.store_info_ios or st.session_state.store_info_android):
        return
    
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

