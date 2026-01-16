"""
App Store / Google Play Store 정보 조회 UI
"""
import streamlit as st
from typing import Optional
from dotenv import load_dotenv
from utils.app_store_helper import get_ios_app_details, get_android_app_details

# .env 파일 로드
load_dotenv()

def main():
    st.set_page_config(
        page_title="앱 스토어 정보 조회",
        page_icon="📱",
        layout="wide"
    )
    
    # 커스텀 CSS
    st.markdown("""
    <style>
    .app-card {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-top: 0;
    }
    /* 구분선 간격 조정 */
    hr {
        margin: 0.25rem 0 !important;
    }
    /* 아이콘과 제목 헤더 정렬 */
    .platform-header-icon {
        display: flex;
        align-items: center;
        justify-content: flex-start;
    }
    .platform-header-title {
        display: flex;
        align-items: center;
        height: 100%;
    }
    .platform-header-title h3 {
        margin: 0;
        line-height: 1.2;
        display: flex;
        align-items: center;
        padding-top: 0.1rem;
    }
    /* Android 텍스트 약간 올리기 */
    .android-header .platform-header-title h3 {
        padding-top: 0 !important;
        margin-top: -0.6rem !important;
        transform: translateY(-0.3rem);
    }
    .android-header {
        display: flex;
        align-items: flex-start;
    }
    [data-testid="column"]:has(.platform-header-title) {
        display: flex;
        align-items: center;
    }
    .info-row {
        display: flex;
        padding: 0.75rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .info-row:last-child {
        border-bottom: none;
    }
    .info-label {
        font-weight: 600;
        color: #666;
        min-width: 120px;
    }
    .info-value {
        color: #1a1a1a;
        flex: 1;
    }
    /* 아이콘과 제목 사이 간격 줄이기 */
    div[data-testid="column"]:has(img[width="80"]) {
        padding-right: 0.5rem !important;
    }
    div[data-testid="column"]:has(h3) {
        padding-left: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Session state 초기화
    if "ios_result" not in st.session_state:
        st.session_state.ios_result = None
    if "android_result" not in st.session_state:
        st.session_state.android_result = None
    if "stored_ios_url" not in st.session_state:
        st.session_state.stored_ios_url = None
    if "stored_android_url" not in st.session_state:
        st.session_state.stored_android_url = None
    
    st.title("📱 앱 스토어 정보 조회")
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("📖 사용 방법")
        st.markdown("""
        1. App Store와 Google Play Store URL을 입력하세요
        2. '조회' 버튼을 클릭하세요
        3. 각 플랫폼의 정보가 오른쪽에 표시됩니다
        """)
        
        st.markdown("---")
        st.subheader("📝 예시 URL")
        st.code("""
App Store:
https://apps.apple.com/us/app/
telegram/id686449807

Google Play:
https://play.google.com/store/
apps/details?id=
org.telegram.messenger
        """, language="")
    
    # 2단 레이아웃 (왼쪽: 입력, 오른쪽: 결과)
    col_left, col_right = st.columns([1, 1.5], gap="large")
    
    # 왼쪽: URL 입력 영역
    with col_left:
        st.subheader("🔗 URL 입력")
        
        # Google Play Store URL
        st.markdown("**🤖 Google Play Store**")
        android_url = st.text_input(
            "Google Play Store URL",
            placeholder="https://play.google.com/store/apps/details?id=...",
            key="android_url",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # App Store URL
        st.markdown("**🍎 App Store**")
        ios_url = st.text_input(
            "App Store URL",
            placeholder="https://apps.apple.com/us/app/...",
            key="ios_url",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 조회 버튼
        fetch_button = st.button("🔍 조회", type="primary", width='stretch', key="fetch_button")
        
        # 조회 버튼 클릭 시 처리
        if fetch_button:
            # Android 조회
            if android_url:
                if "play.google.com" not in android_url:
                    st.error("⚠️ 올바른 Google Play Store URL을 입력해주세요.")
                else:
                    with st.spinner("Google Play Store 정보를 가져오는 중..."):
                        try:
                            android_result = get_android_app_details(android_url)
                            st.session_state.android_result = android_result
                            st.session_state.stored_android_url = android_url
                        except Exception as e:
                            st.error(str(e))
                            st.session_state.android_result = None
                            st.session_state.stored_android_url = None
            else:
                st.session_state.android_result = None
                st.session_state.stored_android_url = None
            
            # iOS 조회
            if ios_url:
                if "apps.apple.com" not in ios_url and "itunes.apple.com" not in ios_url:
                    st.error("⚠️ 올바른 App Store URL을 입력해주세요.")
                else:
                    with st.spinner("App Store 정보를 가져오는 중..."):
                        try:
                            ios_result = get_ios_app_details(ios_url)
                            st.session_state.ios_result = ios_result
                            st.session_state.stored_ios_url = ios_url
                        except Exception as e:
                            st.error(str(e))
                            st.session_state.ios_result = None
                            st.session_state.stored_ios_url = None
            else:
                st.session_state.ios_result = None
                st.session_state.stored_ios_url = None
    
    # 오른쪽: 결과 표시 영역
    with col_right:
        # 결과가 있을 때만 표시
        if st.session_state.ios_result or st.session_state.android_result:
            # Android 결과 표시 (먼저)
            if st.session_state.android_result:
                col_icon_header, col_title_header = st.columns([0.25, 0.75])
                with col_icon_header:
                    st.markdown('<div style="padding-top: 0.3rem;">', unsafe_allow_html=True)
                    st.image("icons/google-play-4.svg", width=180)
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_title_header:
                    st.markdown("""
                    <div style="padding-top: 0.5rem;">
                        <h3 style="margin: 0; line-height: 1.2;">Android (Google Play Store)</h3>
                    </div>
                    """, unsafe_allow_html=True)
                result = st.session_state.android_result
                
                # 아이콘과 제목
                col_icon, col_title = st.columns([0.5, 2.5], gap="small")
                with col_icon:
                    if result.get("icon_url"):
                        st.image(result.get("icon_url"), width=80)
                with col_title:
                    developer_name = result.get('developer', '-')
                    app_name = result.get('name', '알 수 없음')
                    st.markdown(f"### {app_name} <span style='color: #666; font-size: 1rem; font-weight: normal;'>by {developer_name}</span>", unsafe_allow_html=True)
                    if st.session_state.stored_android_url:
                        st.caption(st.session_state.stored_android_url)
                
                st.markdown("---")
                
                # 정보 표시: name, package_name, icon_url, developer, category
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Package Name**")
                    st.text(result.get("package_name", "-"))
                
                with col2:
                    st.markdown(f"**카테고리**")
                    st.text(result.get("category", "-"))
            
            # iOS 결과 표시 (나중에)
            if st.session_state.ios_result:
                if st.session_state.android_result:
                    st.markdown("<br>", unsafe_allow_html=True)
                col_icon_header, col_title_header = st.columns([0.25, 0.75])
                with col_icon_header:
                    st.markdown('<div class="platform-header-icon">', unsafe_allow_html=True)
                    st.image("icons/available-on-the-app-store.svg", width=180)
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_title_header:
                    st.markdown('<div class="platform-header-title">', unsafe_allow_html=True)
                    st.markdown("### iOS (App Store)")
                    st.markdown('</div>', unsafe_allow_html=True)
                result = st.session_state.ios_result
                
                # 아이콘과 제목
                col_icon, col_title = st.columns([0.5, 2.5], gap="small")
                with col_icon:
                    if result.get("icon_url"):
                        st.image(result.get("icon_url"), width=80)
                with col_title:
                    developer_name = result.get('developer', '-')
                    app_name = result.get('name', '알 수 없음')
                    st.markdown(f"### {app_name} <span style='color: #666; font-size: 1rem; font-weight: normal;'>by {developer_name}</span>", unsafe_allow_html=True)
                    if st.session_state.stored_ios_url:
                        st.caption(st.session_state.stored_ios_url)
                
                st.markdown("---")
                
                # 정보 표시: name, app_id, bundle_id, icon_url, developer, category
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Bundle ID**")
                    st.text(result.get("bundle_id", "-"))

                    st.markdown(f"**App ID**")
                    st.text(result.get("app_id", "-"))          

                with col2:
                    st.markdown(f"**카테고리**")
                    st.text(result.get("category", "-"))

if __name__ == "__main__":
    main()