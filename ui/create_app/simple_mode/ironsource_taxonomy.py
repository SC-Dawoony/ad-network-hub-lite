"""IronSource Taxonomy Selection Section"""
import streamlit as st
from network_configs.ironsource_config import IronSourceConfig
from components.one_click.category_matchers import match_ironsource_taxonomy


def render_ironsource_taxonomy_selection():
    """Render IronSource Taxonomy selection section"""
    st.markdown("### 📂 IronSource Taxonomy")
    st.info("💡 IronSource 네트워크를 사용하는 경우, Taxonomy (Sub-genre)를 선택해주세요. 카테고리가 자동으로 매칭되지만 수동으로 변경할 수 있습니다.")
    
    # Initialize taxonomy in session state if not exists
    if "ironsource_taxonomy" not in st.session_state:
        st.session_state.ironsource_taxonomy = "other"
    
    # Get taxonomy options
    ironsource_config = IronSourceConfig()
    taxonomy_options = ironsource_config._get_taxonomies()
    
    # Build hierarchical taxonomy structure
    taxonomy_structure = {
        "Casual": {
            "Hyper Casual": ["stacking", "dexterity", "rising/falling", "swerve", "merge", "idle", ".io", "puzzle", "tap/Timing", "turning", "ball", "other"],
            "Puzzle": ["actionPuzzle", "match3", "bubbleShooter", "jigsaw", "crossword", "word", "trivia", "board", "coloring Games", "hidden Objects", "solitaire", "nonCasinoCardGame", "otherPuzzle"],
            "Arcade": ["platformer", "idler", "shootEmUp", "endlessRunner", "towerDefense", "otherArcade"],
            "Lifestyle": ["customization", "interactiveStory", "music/band", "otherLifestyle"],
            "Simulation": ["adventures", "breeding", "tycoon/crafting", "sandbox", "cooking/timeManagement", "farming", "idleSimulation", "otherSimulation"],
            "Kids & Family": ["kids&Family"],
            "Other Casual": ["otherCasual"]
        },
        "Mid-Core": {
            "Shooter": ["battleRoyale", "classicFPS", "snipers", "tacticalShooter", "otherShooter"],
            "RPG": ["actionRPG", "turnBasedRPG", "fighting", "MMORPG", "puzzleRPG", "survival", "idleRPG", "otherRPG"],
            "Card Games": ["cardBattler"],
            "Strategy": ["4xStrategy", "build&Battle", "MOBA", "syncBattler", "otherStrategy"],
            "Other Mid-Core": ["otherMidCore"]
        },
        "Sports & Racing": {
            "Sports": ["casualSports", "licensedSports"],
            "Racing": ["casualRacing", "simulationRacing", "otherRacing"],
            "Other Sports & Racing": ["otherSports&Racing"]
        }
    }
    
    # Create API value to display name mapping
    api_to_display = {api_value: display_name for display_name, api_value in taxonomy_options}
    
    # Auto-match taxonomy from app category (if not already set)
    # Priority: Android category first, then iOS category
    if st.session_state.ironsource_taxonomy == "other":
        android_category = None
        ios_category = None
        
        if st.session_state.store_info_android:
            android_category = st.session_state.store_info_android.get("category", "")
        if st.session_state.store_info_ios:
            ios_category = st.session_state.store_info_ios.get("category", "")
        
        # Try Android category first (priority)
        app_category = android_category if android_category else ios_category
        
        if app_category:
            # Pass Android category for better matching (if available)
            auto_matched_taxonomy = match_ironsource_taxonomy(
                app_category, 
                taxonomy_options,
                android_category=android_category if android_category else None
            )
            if auto_matched_taxonomy and auto_matched_taxonomy != "other":
                st.session_state.ironsource_taxonomy = auto_matched_taxonomy
                if auto_matched_taxonomy in api_to_display:
                    category_source = "Android" if android_category else "iOS"
                    st.success(f"💡 자동 매칭 ({category_source}): '{app_category}' → '{api_to_display[auto_matched_taxonomy]}'")
    
    # Build flat list of all taxonomy options with category/genre info for display
    taxonomy_display_options = []
    for category, genres in taxonomy_structure.items():
        for genre, sub_genres in genres.items():
            for sub_genre in sub_genres:
                display_name = api_to_display.get(sub_genre, sub_genre)
                taxonomy_display_options.append((f"{category} > {genre} > {display_name}", sub_genre))
    
    # Create selectbox with hierarchical display
    selected_index = 0
    for idx, (display_name, api_value) in enumerate(taxonomy_display_options):
        if api_value == st.session_state.ironsource_taxonomy:
            selected_index = idx
            break
    
    selected_taxonomy_display = st.selectbox(
        "Taxonomy (Sub-genre)*",
        options=[opt[0] for opt in taxonomy_display_options],
        index=selected_index,
        key="ironsource_taxonomy_select",
        help="IronSource Taxonomy를 선택하세요. 계층 구조: Category > Genre > Sub-genre"
    )
    
    # Extract API value from selected display
    for display_name, api_value in taxonomy_display_options:
        if display_name == selected_taxonomy_display:
            st.session_state.ironsource_taxonomy = api_value
            break
    
    return st.session_state.ironsource_taxonomy

