"""Category matching utilities for one-click workflow"""
from typing import List, Tuple, Optional


def match_ironsource_taxonomy(category: str, taxonomy_options: List[Tuple[str, str]]) -> Optional[str]:
    """Match App Store category to IronSource taxonomy
    
    Args:
        category: App Store category name
        taxonomy_options: List of (display_name, api_value) tuples
        
    Returns:
        Matched taxonomy display name or None
    """
    if not category:
        return None
    
    category_lower = category.lower()
    
    # Simple keyword matching
    for display_name, api_value in taxonomy_options:
        display_lower = display_name.lower()
        # Check if category contains key words from taxonomy
        if category_lower in display_lower or display_lower in category_lower:
            return display_name
    
    # Default to first option if no match
    if taxonomy_options:
        return taxonomy_options[0][0]
    
    return None


def match_fyber_android_category(category: str, category_options: List[Tuple[str, str]]) -> Optional[str]:
    """Match App Store category to Fyber Android category
    
    Args:
        category: App Store category name
        category_options: List of (display_name, api_value) tuples
        
    Returns:
        Matched category display name or None
    """
    if not category:
        return None
    
    category_lower = category.lower()
    
    # Simple keyword matching
    for display_name, api_value in category_options:
        display_lower = display_name.lower()
        if category_lower in display_lower or display_lower in category_lower:
            return display_name
    
    # Default to first option if no match
    if category_options:
        return category_options[0][0]
    
    return None


def match_fyber_ios_category(
    ios_category: str, 
    android_category: str, 
    ios_category_options: List[Tuple[str, str]]
) -> Optional[str]:
    """Match App Store categories to Fyber iOS category
    
    Args:
        ios_category: iOS App Store category
        android_category: Android Play Store category (optional)
        ios_category_options: List of (display_name, api_value) tuples
        
    Returns:
        Matched iOS category display name or None
    """
    if not ios_category:
        return None
    
    ios_category_lower = ios_category.lower()
    
    # Special handling for Games category
    if ios_category_lower in ["games", "game"] and android_category:
        android_category_lower = android_category.lower()
        # Try to match based on Android category
        for display_name, api_value in ios_category_options:
            display_lower = display_name.lower()
            if android_category_lower in display_lower or display_lower in android_category_lower:
                return display_name
    
    # Fallback to simple iOS category matching
    return match_fyber_android_category(ios_category, ios_category_options)