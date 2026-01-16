"""App Match Name (Identifier) Selection Section"""
import streamlit as st


def render_identifier_selection(android_package: str, ios_bundle_id: str):
    """Render identifier selection section for Ad Unit naming
    
    Args:
        android_package: Android package name
        ios_bundle_id: iOS bundle ID
    
    Returns:
        str: Selected identifier value (lowercase)
    """
    # Initialize selection in session state if not exists
    if "ios_ad_unit_identifier" not in st.session_state:
        # Default: use Android Package Name (last part), convert to lowercase
        android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
        st.session_state.ios_ad_unit_identifier = {
            "source": "android_package",
            "value": android_package_last.lower()
        }
    
    # Show current selection status
    selected_value = st.session_state.ios_ad_unit_identifier.get("value", "")
    if selected_value:
        st.info(f"**선택된 값:** `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
    
    # Define dialog function
    @st.dialog("🔀 App match name 선택")
    def identifier_selection_dialog():
        st.markdown("### 🔀 App match name")
        st.info("💡 Android Package Name과 iOS Bundle ID가 다릅니다. Ad Unit 이름 생성 시 어떤 값을 사용할지 선택하거나 직접 입력하세요.")
        
        # Extract last part of Android Package Name
        android_package_last = android_package.split('.')[-1] if '.' in android_package else android_package
        ios_bundle_id_last = ios_bundle_id.split('.')[-1] if '.' in ios_bundle_id else ios_bundle_id
        
        # Selection options (display original case, but store lowercase)
        selection_options = [
            f"Android Package Name: `{android_package_last}`",
            f"iOS Bundle ID: `{ios_bundle_id_last}`",
            "직접 입력"
        ]
        
        # Get current selection
        current_selection = st.session_state.ios_ad_unit_identifier.get("source", "android_package")
        if current_selection == "android_package":
            current_index = 0
        elif current_selection == "ios_bundle_id":
            current_index = 1
        else:
            current_index = 2
        
        selected_option = st.radio(
            "선택하세요:",
            options=selection_options,
            index=current_index,
            key="ios_ad_unit_identifier_radio_dialog"
        )
        
        # Update session state based on selection (convert to lowercase)
        if selected_option.startswith("Android Package Name"):
            st.session_state.ios_ad_unit_identifier = {
                "source": "android_package",
                "value": android_package_last.lower()
            }
        elif selected_option.startswith("iOS Bundle ID"):
            st.session_state.ios_ad_unit_identifier = {
                "source": "ios_bundle_id",
                "value": ios_bundle_id_last.lower()
            }
        else:  # 직접 입력
            custom_value = st.text_input(
                "직접 입력:",
                value=st.session_state.ios_ad_unit_identifier.get("value", ""),
                key="ios_ad_unit_identifier_custom_dialog",
                help="Ad Unit 이름 생성에 사용할 식별자를 직접 입력하세요 (소문자로 저장됩니다)"
            )
            if custom_value:
                st.session_state.ios_ad_unit_identifier = {
                    "source": "custom",
                    "value": custom_value.lower()
                }
        
        # Show preview
        selected_value = st.session_state.ios_ad_unit_identifier.get("value", "")
        if selected_value:
            st.success(f"✅ 선택된 값: `{selected_value}` (이 값이 Android와 iOS Ad Unit 이름 생성에 사용됩니다)")
        
        # Close dialog buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 확인", key="confirm_identifier_dialog", use_container_width=True, type="primary"):
                st.rerun()
        with col2:
            if st.button("❌ 취소", key="cancel_identifier_dialog", use_container_width=True):
                st.rerun()
    
    # Button to open dialog
    if st.button("🔀 App match name 선택", key="open_identifier_dialog", use_container_width=True):
        identifier_selection_dialog()
    
    return st.session_state.ios_ad_unit_identifier.get("value", "")


def get_selected_identifier() -> str:
    """Get the currently selected identifier value
    
    Returns:
        str: Selected identifier value (lowercase), or empty string if not set
    """
    return st.session_state.ios_ad_unit_identifier.get("value", "") if "ios_ad_unit_identifier" in st.session_state else ""

