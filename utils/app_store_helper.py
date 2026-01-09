"""Helper functions for App Store information retrieval"""
import requests
import re
from typing import Optional

# google-play-scraper 라이브러리 import (선택적)
try:
    from google_play_scraper import app
    PLAY_STORE_AVAILABLE = True
except ImportError:
    PLAY_STORE_AVAILABLE = False


def get_ios_app_details(app_store_url: str) -> Optional[dict]:
    """Extract app details from App Store URL - 필요한 필드만: name, app_id, bundle_id, icon_url, developer, category"""
    match = re.search(r'/id(\d+)', app_store_url)
    if not match:
        raise ValueError("Invalid App Store URL")
    
    app_id = match.group(1)
    itunes_url = f"https://itunes.apple.com/lookup?id={app_id}"
    
    try:
        response = requests.get(itunes_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result_count = data.get("resultCount", 0)
            
            if result_count == 0:
                return None
            
            result = data["results"][0]
            
            # 필요한 필드만 반환: name, app_id, bundle_id, icon_url, developer, category
            app_details = {
                "app_id": app_id,
                "name": result.get("trackName"),
                "bundle_id": result.get("bundleId"),
                "icon_url": result.get("artworkUrl512"),
                "developer": result.get("artistName"),
                "category": result.get("primaryGenreName"),
            }
            
            return app_details
        else:
            return None
            
    except Exception as e:
        raise Exception(f"오류 발생: {e}")


def get_android_app_details(play_store_url: str) -> Optional[dict]:
    """Extract app details from Google Play Store URL - 필요한 필드만: name, package_name, icon_url, developer, category"""
    if not PLAY_STORE_AVAILABLE:
        raise Exception("⚠️ google-play-scraper 라이브러리가 설치되지 않았습니다.\n설치 방법: pip install google-play-scraper")
    
    match = re.search(r'id=([a-zA-Z0-9._]+)', play_store_url)
    if not match:
        raise ValueError("Invalid Play Store URL")
    
    package_name = match.group(1)
    
    try:
        result = app(package_name, lang='en', country='us')
        
        # google_play_scraper는 딕셔너리를 반환합니다
        # 아이콘 URL 가져오기
        icon_url = result.get("icon") if isinstance(result, dict) else None
        
        # 디버깅: 아이콘 URL이 없을 경우 사용 가능한 키 확인
        if not icon_url and isinstance(result, dict):
            # icon 필드가 없는 경우 다른 가능한 필드명 확인
            possible_icon_keys = [k for k in result.keys() if 'icon' in k.lower()]
            if possible_icon_keys:
                icon_url = result.get(possible_icon_keys[0])
        
        # 필요한 필드만 반환: name, package_name, icon_url, developer, category
        app_details = {
            "package_name": package_name,
            "name": result.get("title", "알 수 없음"),
            "icon_url": icon_url,
            "developer": result.get("developer", "-"),
            "category": result.get("genre", "-"),
        }
        
        return app_details
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise Exception(f"앱을 찾을 수 없습니다: {package_name}")
        else:
            raise Exception(f"오류 발생: {error_msg}")

