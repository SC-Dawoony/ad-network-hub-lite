"""Wrapper for create_unit_common to maintain backward compatibility

This module redirects imports to maintain compatibility with existing code.
The actual implementation will gradually move to ui/create_unit/networks/ modules.
"""
# For now, import from original location
# TODO: Gradually migrate to ui/create_unit/networks/ modules
from components.create_unit_common import render_create_unit_common_ui

# Re-export for backward compatibility
__all__ = ['render_create_unit_common_ui']

