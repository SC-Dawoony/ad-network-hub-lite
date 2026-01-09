"""Create App - Simple Mode (Multiple Networks at Once)"""
import streamlit as st
import logging
from utils.session_manager import SessionManager
from components.create_app_new_ui import render_new_create_app_ui

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Create App (Simple)",
    page_icon="🚀",
    layout="wide"
)

# Initialize session
SessionManager.initialize()

st.title("🚀 Create App (Simple Mode)")
st.markdown("**Store URL만 입력하면 여러 네트워크에 자동으로 앱을 생성할 수 있습니다.**")

st.markdown("---")

# Render the new simplified UI
render_new_create_app_ui()

# Help section
with st.expander("ℹ️ 사용 방법"):
    st.markdown("""
    ### 간편 모드 사용법
    
    1. **Store URL 입력**
       - Android: Google Play Store URL 입력
       - iOS: App Store URL 입력
       - 최소 하나의 URL은 필수입니다
    
    2. **앱 정보 조회**
       - "🔍 앱 정보 조회" 버튼을 클릭하면 자동으로 앱 정보를 가져옵니다
    
    3. **네트워크 선택**
       - 앱을 생성할 네트워크를 선택하세요 (여러 개 선택 가능)
       - 체크박스로 원하는 네트워크를 선택합니다
    
    4. **앱 생성**
       - "🚀 선택한 네트워크에 앱 생성" 버튼을 클릭하면
       - 선택한 모든 네트워크에 순차적으로 앱이 생성됩니다
    
    ### 특징
    
    - ✅ **자동 파라미터 매핑**: App Store 정보를 자동으로 네트워크별 파라미터로 변환
    - ✅ **일괄 처리**: 여러 네트워크를 한 번에 처리
    - ✅ **진행 상황 표시**: 각 네트워크별 처리 상태를 실시간으로 확인
    - ✅ **기본값 자동 설정**: 필수 필드에 기본값이 자동으로 설정됩니다
    
    ### 참고사항
    
    - 일부 네트워크는 추가 필드가 필요할 수 있습니다
    - 더 세밀한 제어가 필요하면 "Create App & Unit" 페이지를 사용하세요
    """)

