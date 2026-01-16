"""Payload Preview UI Rendering"""
import streamlit as st


def render_payload_preview(preview_data: dict, has_errors: bool = False):
    """Render payload preview display section
    
    Args:
        preview_data: Dictionary of preview data per network
        has_errors: Whether there are any errors in preview data
    """
    st.markdown("### 3️⃣ Payload 미리보기")
    st.markdown("각 네트워크별로 전송될 API Payload를 확인하세요.")
    
    # Store preview_data in session state if not already stored
    if "preview_data" not in st.session_state:
        st.session_state.preview_data = preview_data
    
    # Display previews
    for network_key, preview_info in preview_data.items():
        network_display = preview_info["display"]
        
        # AppLovin: Show info message instead of payload
        if preview_info.get("skip_app_creation"):
            st.markdown(f"#### 📡 {network_display}")
            st.info(f"💡 {preview_info.get('info_message', '')}")
            st.warning("⚠️ **주의사항:** 이미 활성화된 앱/플랫폼/광고 형식 조합에 대해서는 이 API를 통해 추가 Ad Unit을 생성할 수 없습니다. 추가 생성은 대시보드에서 직접 진행해주세요.")
            st.markdown("---")
            continue
        
        if "error" in preview_info:
            st.error(f"❌ **{network_display}**: {preview_info['error']}")
            with st.expander(f"📋 {network_display} - 매핑된 파라미터", expanded=False):
                st.json(preview_info.get("params", {}))
        else:
            st.markdown(f"#### 📡 {network_display}")
            
            # Show mapped parameters
            with st.expander(f"📋 {network_display} - 매핑된 파라미터", expanded=False):
                st.json(preview_info.get("params", {}))
            
            # Show payloads
            for platform, payload in preview_info.get("payloads", {}).items():
                if isinstance(payload, dict) and "error" in payload:
                    st.error(f"⚠️ {platform} Payload 생성 실패: {payload['error']}")
                else:
                    platform_label = platform if platform != "default" else "Default"
                    with st.expander(f"📤 {network_display} - {platform_label} App Payload", expanded=False):
                        st.json(payload)
            
            # Show ad unit payloads if available
            unit_payloads = preview_info.get("unit_payloads", {})
            if unit_payloads:
                for platform, platform_units in unit_payloads.items():
                    platform_label = platform if platform != "default" else "Default"
                    with st.expander(f"📦 {network_display} - {platform_label} Ad Unit Payloads (RV, IS, BN)", expanded=False):
                        st.info("💡 `{APP_CODE}`는 앱 생성 후 실제 App ID로 자동 교체됩니다.")
                        for slot_type, unit_payload in platform_units.items():
                            st.markdown(f"**{slot_type} Unit:**")
                            st.json(unit_payload)
            
            st.markdown("---")
    
    if has_errors:
        st.warning("⚠️ 일부 네트워크에 오류가 있습니다. 문제를 해결한 후 다시 시도해주세요.")
        st.info("💡 일부 네트워크는 추가 정보가 필요할 수 있습니다. 기존 Create App 페이지를 사용해주세요.")
    
    st.divider()

