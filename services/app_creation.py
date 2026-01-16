"""App Creation Service - Business logic for app and unit creation"""
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def extract_app_info_from_response(network_key: str, response: Dict, mapped_params: Dict) -> Optional[Dict]:
    """Extract app info (appId, appCode, gameId, etc.) from create app response
    
    Args:
        network_key: Network identifier
        response: Create app API response
        mapped_params: Mapped parameters used for app creation
    
    Returns:
        Dict with app info (appCode, appId, appKey, etc.) or None
    """
    if not response or not isinstance(response, dict):
        return None
    
    result = response.get('result', {})
    if not result:
        result = response
    
    app_info = {}
    
    # Network-specific extraction
    if network_key == "ironsource":
        # IronSource: appKey from result
        app_info["appKey"] = result.get("appKey") or response.get("appKey")
        app_info["appCode"] = app_info["appKey"]
    elif network_key == "mintegral":
        # Mintegral: app_id from result.result
        app_id = result.get("app_id") or result.get("id") or result.get("appId")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "inmobi":
        # InMobi: appId from result.data or result
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else result
        app_id = data.get("appId") or data.get("id") or result.get("appId")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "bigoads":
        # BigOAds: appCode from result.result
        app_code = result.get("appCode") or response.get("appCode")
        app_info["appCode"] = app_code
    elif network_key == "fyber":
        # Fyber: appId from result.result
        app_id = result.get("appId") or result.get("id")
        app_info["appId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "unity":
        # Unity: gameId from result.result.stores
        stores = result.get("stores", {})
        apple_store = stores.get("apple", {}) if isinstance(stores.get("apple"), dict) else {}
        google_store = stores.get("google", {}) if isinstance(stores.get("google"), dict) else {}
        apple_game_id = apple_store.get("gameId")
        google_game_id = google_store.get("gameId")
        project_id = result.get("id")
        app_info["apple_gameId"] = apple_game_id
        app_info["google_gameId"] = google_game_id
        app_info["project_id"] = project_id
        app_info["appCode"] = str(apple_game_id) if apple_game_id else (str(google_game_id) if google_game_id else str(project_id) if project_id else None)
    elif network_key == "pangle":
        # Pangle: app_id from result.result (normalized response structure)
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
        app_id = result_data.get("app_id")
        app_info["appId"] = app_id
        app_info["siteId"] = app_id
        app_info["appCode"] = str(app_id) if app_id else None
    elif network_key == "vungle":
        # Vungle: vungleAppId from result (response is the app object itself)
        result_data = result.get("result", {}) if isinstance(result.get("result"), dict) else result
        vungle_app_id = result_data.get("vungleAppId") or result_data.get("id")
        app_info["vungleAppId"] = vungle_app_id
        app_info["appId"] = vungle_app_id
        app_info["appCode"] = str(vungle_app_id) if vungle_app_id else None
        app_info["platform"] = result_data.get("platform", "")  # "ios" or "android"
        app_info["name"] = result_data.get("name", "")
        
        # Extract platform-specific package name/bundle ID from mapped_params
        platform_value = result_data.get("platform", "").lower()
        if platform_value == "android":
            app_info["pkgName"] = mapped_params.get("android_store_id", mapped_params.get("androidPackageName", ""))
            app_info["platformStr"] = "android"
        elif platform_value == "ios":
            app_info["bundleId"] = mapped_params.get("ios_store_id", mapped_params.get("iosAppId", ""))
            app_info["pkgName"] = ""  # iOS doesn't use pkgName
            app_info["platformStr"] = "ios"
    else:
        # Default: try common fields
        app_code = result.get("appCode") or result.get("appId") or result.get("appKey") or result.get("id")
        app_info["appCode"] = app_code
    
    # Add common fields
    app_info["name"] = result.get("name") or mapped_params.get("name") or mapped_params.get("app_name") or "Unknown"
    
    # Extract platform-specific package name and bundle ID for all networks
    # Android: use package name, iOS: use bundle ID
    platform_str = mapped_params.get("platformStr") or mapped_params.get("platform", "android")
    platform_value = platform_str.lower() if isinstance(platform_str, str) else "android"
    
    # For multi-platform networks, extract from platform-specific fields in mapped_params
    if network_key in ["ironsource", "inmobi", "bigoads", "fyber", "mintegral", "pangle"]:
        # Try to get from platform-specific fields first
        if platform_value == "android" or "Android" in str(platform_str):
            app_info["pkgName"] = mapped_params.get("android_package", mapped_params.get("androidPkgName", mapped_params.get("android_store_id", mapped_params.get("package", ""))))
            app_info["bundleId"] = ""  # Android doesn't use bundleId
            app_info["platformStr"] = "android"
        elif platform_value == "ios" or "iOS" in str(platform_str) or "IOS" in str(platform_str):
            app_info["pkgName"] = ""  # iOS doesn't use pkgName
            app_info["bundleId"] = mapped_params.get("ios_bundle_id", mapped_params.get("iosPkgName", mapped_params.get("ios_store_id", mapped_params.get("bundle", mapped_params.get("bundleId", "")))))
            app_info["platformStr"] = "ios"
        else:
            # Fallback: try generic fields
            app_info["pkgName"] = mapped_params.get("pkgName") or mapped_params.get("package", "")
            app_info["bundleId"] = mapped_params.get("bundleId") or mapped_params.get("bundle", "")
            app_info["platformStr"] = platform_value
    else:
        # Single platform or other networks: use generic fields
        app_info["pkgName"] = mapped_params.get("pkgName") or mapped_params.get("package", "")
        app_info["bundleId"] = mapped_params.get("bundleId") or mapped_params.get("bundle", "")
        app_info["platformStr"] = platform_value
    
    return app_info if app_info.get("appCode") else None


def map_store_info_to_network_params(
    ios_info: Optional[Dict],
    android_info: Optional[Dict],
    network: str,
    config
) -> Dict:
    """Map App Store info to network-specific parameters
    
    Args:
        ios_info: iOS app details from App Store
        android_info: Android app details from Play Store
        network: Network identifier
        config: Network configuration object
    
    Returns:
        Dictionary with network-specific parameters filled in
    """
    import streamlit as st  # Note: Service layer depends on Streamlit session state for taxonomy
    # TODO: Refactor to remove Streamlit dependency by passing taxonomy as parameter
    
    params = {}
    
    # Common fields that most networks use
    app_name = None
    if ios_info:
        app_name = ios_info.get("name")
    if not app_name and android_info:
        app_name = android_info.get("name")
    
    # Network-specific mapping
    if network == "ironsource":
        params["appName"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        
        # Use taxonomy from session state (user-selected or auto-matched)
        # If not in session state, try to match from App Store category
        if "ironsource_taxonomy" in st.session_state:
            params["taxonomy"] = st.session_state.ironsource_taxonomy
        else:
            # Map App Store category to IronSource taxonomy
            from components.one_click.category_matchers import match_ironsource_taxonomy
            
            # Get category from Android first (priority), then iOS
            android_category = None
            ios_category = None
            if android_info:
                android_category = android_info.get("category", "")
            if ios_info:
                ios_category = ios_info.get("category", "")
            
            # Use Android category if available (priority)
            app_category = android_category if android_category else ios_category
            
            # Get taxonomy options from config
            taxonomy_options = config._get_taxonomies() if hasattr(config, '_get_taxonomies') else []
            
            # Match category to taxonomy (pass Android category for better matching)
            matched_taxonomy = match_ironsource_taxonomy(
                app_category, 
                taxonomy_options,
                android_category=android_category if android_category else None
            ) if app_category else "other"
            params["taxonomy"] = matched_taxonomy
            # Store in session state for future use
            st.session_state.ironsource_taxonomy = matched_taxonomy
        
        params["coppa"] = 0  # Default: Not child-directed
    
    elif network == "inmobi":
        params["appName"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Default values
        params["childDirected"] = 2  # Not child-directed
        params["locationAccess"] = True
    
    elif network == "bigoads":
        params["name"] = app_name or ""
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
            params["iosPkgName"] = ios_info.get("bundle_id", "")
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
            params["androidPkgName"] = android_info.get("package_name", "")
        # Default values (from BigOAdsConfig defaults)
        params["mediaType"] = 1  # Always Application (1)
        params["mediationPlatform"] = [1]  # Default: MAX
        params["category"] = "GAME_CASUAL"  # Default category
        params["coppaOption"] = 1  # Default: Not child-directed
        params["screenDirection"] = 0  # Default: Vertical
    
    elif network == "fyber":
        params["name"] = app_name or ""
        
        # Import category matchers
        from components.one_click.category_matchers import match_fyber_android_category, match_fyber_ios_category
        
        if ios_info:
            params["iosStoreUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
            params["iosBundle"] = ios_info.get("bundle_id", "")
            # Map iOS category from App Store to Fyber iOS category
            ios_category = ios_info.get("category", "")
            android_category = android_info.get("category", "") if android_info else ""
            fyber_ios_categories = config._get_categories("ios")
            matched_ios_category = match_fyber_ios_category(ios_category, android_category, fyber_ios_categories)
            params["iosCategory1"] = matched_ios_category or "Games"  # Default to "Games" if no match
        if android_info:
            params["androidStoreUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
            params["androidBundle"] = android_info.get("package_name", "")
            # Map Android category from Play Store to Fyber Android category
            android_category = android_info.get("category", "")
            fyber_android_categories = config._get_categories("android")
            matched_android_category = match_fyber_android_category(android_category, fyber_android_categories)
            params["androidCategory1"] = matched_android_category or "Games - Casual"  # Default to "Games - Casual" if no match
        params["coppa"] = "false"  # Default: Not child-directed
    
    elif network == "pangle":
        # Pangle uses platform-specific app names
        # Store both platform app names and URLs for multi-platform support
        if ios_info:
            params["iosAppName"] = ios_info.get("name", "")
            params["iosDownloadUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["androidAppName"] = android_info.get("name", "")
            params["androidDownloadUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Fallback to common app_name if platform-specific names not available
        params["app_name"] = app_name or ""
        # Note: user_id and role_id are NOT included in params
        # They will be added by pangle_api.py from environment variables
        # This ensures consistency and prevents params from overriding .env values
        # Match app_category_code from iOS and Android categories
        ios_category = ios_info.get("category", "") if ios_info else None
        android_category = android_info.get("category", "") if android_info else None
        params["app_category_code"] = config.match_category_code(ios_category, android_category)
        params["coppa_value"] = 0  # Default: For users aged 13 and above
        params["mask_rule_ids"] = "531582"  # Default mask rule IDs
    
    elif network == "mintegral":
        # Mintegral requires separate payloads for iOS and Android
        # Store base params separately for each platform
        params["app_name"] = app_name or ""
        # Note: os, package, store_url will be set per platform in build_app_payload
        # Default values (common for both platforms)
        params["appType"] = 1  # Application
        params["category"] = "Games"
        params["is_live_in_store"] = 1  # Default: Live in store (requires store_url)
        params["coppa"] = 0  # Default: Not child-directed
        
        # Store platform-specific info separately
        if ios_info:
            params["ios_itunesId"] = ios_info.get("app_id", "")
            params["ios_package"] = ios_info.get("bundle_id", "")
            params["ios_store_url"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["android_package"] = android_info.get("package_name", "")
            params["android_store_url"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
    
    elif network == "unity":
        params["name"] = app_name or ""
        if ios_info:
            params["apple_storeId"] = ios_info.get("app_id", "")
            params["apple_storeUrl"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["google_storeId"] = android_info.get("package_name", "")
            params["google_storeUrl"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
        # Default values
        params["adsProvider"] = ["max"]  # Default: MAX
        params["coppa"] = "non_compliant"  # Default
    
    elif network == "vungle":
        # Vungle requires separate payloads for iOS and Android
        # Store base params separately for each platform
        params["name"] = app_name or ""
        
        # Store platform-specific info separately
        if ios_info:
            params["ios_name"] = ios_info.get("name", "")
            params["ios_store_id"] = ios_info.get("app_id", "")  # App ID for iOS
            params["ios_store_url"] = f"https://apps.apple.com/us/app/id{ios_info.get('app_id')}"
        if android_info:
            params["android_name"] = android_info.get("name", "")
            params["android_store_id"] = android_info.get("package_name", "")  # Package name for Android
            params["android_store_url"] = f"https://play.google.com/store/apps/details?id={android_info.get('package_name')}"
    
    return params

