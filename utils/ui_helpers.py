"""UI helper functions for Streamlit"""
import streamlit as st
import logging
import sys
import json
from typing import Dict, Optional
from utils.helpers import mask_sensitive_data

logger = logging.getLogger(__name__)


def handle_api_response(response: Dict, network: Optional[str] = None) -> Optional[Dict]:
    """Handle API response and display result
    
    Args:
        response: API response dictionary with status, code, msg, result
        network: Optional network identifier (e.g., "vungle") to skip masking
        
    Returns:
        Result dictionary if success, None otherwise
    """
    # Log full response to console
    logger.info(f"API Response: {json.dumps(mask_sensitive_data(response), indent=2)}")
    print(f"[API Response] {json.dumps(mask_sensitive_data(response), indent=2)}", file=sys.stderr)
    
    if response.get('status') == 0 or response.get('code') == 0:
        st.success("✅ Success!")
        
        # Display full response in expander (no masking for Vungle)
        with st.expander("📥 Full API Response", expanded=False):
            if network == "vungle":
                st.json(response)
            else:
                st.json(mask_sensitive_data(response))
        
        result = response.get('result', {})
        if result:
            # Display result separately for clarity (no masking for Vungle)
            st.subheader("📝 Result Data")
            if network == "vungle":
                st.json(result)
            else:
                st.json(mask_sensitive_data(result))
        
        return result
    else:
        error_msg = response.get('msg', 'Unknown error')
        error_code = response.get('code', 'N/A')
        
        # Parse and improve error messages for better user experience
        user_friendly_msg = error_msg
        if error_code == "105" or error_code == 105:
            if "app auditing" in error_msg.lower() or "app audit" in error_msg.lower():
                if "audit fail" in error_msg.lower():
                    user_friendly_msg = "⚠️ App audit failed. Please ensure your app has passed the audit before creating slots."
                else:
                    user_friendly_msg = "⏳ App is currently under audit. Please wait for the audit to complete before creating slots."
            else:
                user_friendly_msg = f"System error: {error_msg}"
        
        # Log error to console
        logger.error(f"API Error: {error_code} - {error_msg}")
        print(f"[API Error] {error_code} - {error_msg}", file=sys.stderr)
        
        st.error(f"❌ Error: {error_code} - {user_friendly_msg}")
        
        # Show original error message in expander for debugging
        with st.expander("📥 Full Error Response", expanded=True):
            st.json(mask_sensitive_data(response))
            st.info(f"**Original error message:** {error_msg}")
            
            # Show validation errors if available
            if response.get("errors"):
                st.subheader("❌ Validation Errors")
                st.json(response.get("errors"))
            if response.get("errorDetails"):
                st.subheader("❌ Error Details")
                st.json(response.get("errorDetails"))
            if response.get("validationErrors"):
                st.subheader("❌ Validation Errors")
                st.json(response.get("validationErrors"))
            if response.get("fieldErrors"):
                st.subheader("❌ Field Errors")
                st.json(response.get("fieldErrors"))
        
        return None