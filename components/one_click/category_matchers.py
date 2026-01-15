"""Category matching utilities for one-click workflow"""
from typing import List, Tuple, Optional


def match_ironsource_taxonomy(category: str, taxonomy_options: List[Tuple[str, str]], android_category: Optional[str] = None) -> Optional[str]:
    """Match App Store category to IronSource taxonomy
    
    Args:
        category: App Store category name (from App Store or Play Store)
        taxonomy_options: List of (display_name, api_value) tuples
        android_category: Android category name (optional, used for better matching)
        
    Returns:
        Matched taxonomy API value (not display name) or "other" if no match
    """
    if not category:
        return "other"
    
    # Use Android category if available (priority)
    category_to_match = android_category if android_category else category
    category_lower = category_to_match.lower().strip()
    
    # Build mapping dictionary for quick lookup
    taxonomy_map = {}
    for display_name, api_value in taxonomy_options:
        taxonomy_map[api_value] = display_name
    
    # Detailed category to taxonomy mapping
    category_to_taxonomy = {
        # Puzzle games
        "puzzle": "puzzle",
        "word": "word",
        "trivia": "trivia",
        "board": "board",
        "jigsaw": "jigsaw",
        "crossword": "crossword",
        "match": "match3",
        "match-3": "match3",
        "match 3": "match3",
        "bubble": "bubbleShooter",
        "solitaire": "solitaire",
        "coloring": "coloring Games",
        "hidden object": "hidden Objects",
        "hiddenobjects": "hidden Objects",
        "card game": "nonCasinoCardGame",
        "action puzzle": "actionPuzzle",
        "action-puzzle": "actionPuzzle",
        
        # Arcade games
        "arcade": "otherArcade",
        "platformer": "platformer",
        "idle": "idle",
        "idler": "idler",
        "endless runner": "endlessRunner",
        "endless-runner": "endlessRunner",
        "tower defense": "towerDefense",
        "tower-defense": "towerDefense",
        "shoot em up": "shootEmUp",
        "shooter": "shootEmUp",
        
        # Casual games
        "casual": "otherCasual",
        "kids": "kids&Family",
        "family": "kids&Family",
        "kids & family": "kids&Family",
        
        # Strategy games
        "strategy": "otherStrategy",
        "4x": "4xStrategy",
        "moba": "MOBA",
        "card battler": "cardBattler",
        "card-battler": "cardBattler",
        "build & battle": "build&Battle",
        "build and battle": "build&Battle",
        "sync battler": "syncBattler",
        
        # RPG games
        "rpg": "otherRPG",
        "action rpg": "actionRPG",
        "action-rpg": "actionRPG",
        "turn-based rpg": "turnBasedRPG",
        "turn based rpg": "turnBasedRPG",
        "mmorpg": "MMORPG",
        "puzzle rpg": "puzzleRPG",
        "puzzle-rpg": "puzzleRPG",
        "survival": "survival",
        "idle rpg": "idleRPG",
        "idle-rpg": "idleRPG",
        
        # Shooter games
        "fps": "classicFPS",
        "battle royale": "battleRoyale",
        "battle-royale": "battleRoyale",
        "sniper": "snipers",
        "tactical shooter": "tacticalShooter",
        "tactical-shooter": "tacticalShooter",
        
        # Sports & Racing
        "sports": "casualSports",
        "racing": "casualRacing",
        "simulation racing": "simulationRacing",
        "simulation-racing": "simulationRacing",
        
        # Simulation games
        "simulation": "otherSimulation",
        "tycoon": "tycoon/crafting",
        "crafting": "tycoon/crafting",
        "sandbox": "sandbox",
        "farming": "farming",
        "cooking": "cooking/timeManagement",
        "time management": "cooking/timeManagement",
        "time-management": "cooking/timeManagement",
        "idle simulation": "idleSimulation",
        "idle-simulation": "idleSimulation",
        "breeding": "breeding",
        "adventure": "adventures",
        
        # Lifestyle
        "music": "music/band",
        "band": "music/band",
        "customization": "customization",
        "interactive story": "interactiveStory",
        "interactive-story": "interactiveStory",
        
        # Special categories
        ".io": ".io",
        "io game": ".io",
        "merge": "merge",
        "stacking": "stacking",
        "dexterity": "dexterity",
        "ball": "ball",
        "turning": "turning",
        "tap": "tap/Timing",
        "timing": "tap/Timing",
        "swerve": "swerve",
        "rising": "rising/falling",
        "falling": "rising/falling",
        "ar": "aR/locationBased",
        "location based": "aR/locationBased",
        "location-based": "aR/locationBased",
        "fighting": "fighting",
    }
    
    # Try exact match first
    if category_lower in category_to_taxonomy:
        taxonomy_value = category_to_taxonomy[category_lower]
        if taxonomy_value in taxonomy_map:
            return taxonomy_value
    
    # Try partial matching
    for app_store_term, taxonomy_value in category_to_taxonomy.items():
        if app_store_term in category_lower or category_lower in app_store_term:
            if taxonomy_value in taxonomy_map:
                return taxonomy_value
    
    # Try matching against taxonomy display names (case-insensitive)
    for display_name, api_value in taxonomy_options:
        display_lower = display_name.lower()
        # Check if category contains key words from taxonomy
        if category_lower in display_lower or display_lower in category_lower:
            return api_value
        
        # Also check if any word from taxonomy appears in category
        taxonomy_words = display_lower.split()
        category_words = category_lower.split()
        if any(word in category_lower for word in taxonomy_words if len(word) > 3):
            return api_value
    
    # Default to "other" if no match found
    return "other"


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