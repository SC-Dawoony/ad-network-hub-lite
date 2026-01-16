# Compatibility layer: Redirect to new API base
# This allows existing code to continue using the old import path
# TODO: Update all imports to use api.base instead of utils.network_apis.base_network_api

from api.base import BaseNetworkAPI

__all__ = ['BaseNetworkAPI']
