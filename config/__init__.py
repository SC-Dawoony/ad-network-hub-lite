"""Network configuration registry"""
from config.base_config import NetworkConfig, Field, ConditionalField
from config.networks.bigoads_config import BigOAdsConfig
from config.networks.ironsource_config import IronSourceConfig
from config.networks.pangle_config import PangleConfig
from config.networks.mintegral_config import MintegralConfig
from config.networks.inmobi_config import InMobiConfig
from config.networks.fyber_config import FyberConfig
from config.networks.applovin_config import AppLovinConfig
from config.networks.unity_config import UnityConfig
from config.networks.vungle_config import VungleConfig

# Network registry
NETWORK_REGISTRY = {
    'bigoads': BigOAdsConfig(),
    'ironsource': IronSourceConfig(),
    'pangle': PangleConfig(),
    'mintegral': MintegralConfig(),
    'inmobi': InMobiConfig(),
    'fyber': FyberConfig(),
    'applovin': AppLovinConfig(),
    'unity': UnityConfig(),
    'vungle': VungleConfig(),
    # Future networks will be added here
}

def get_network_config(network_name: str) -> NetworkConfig:
    """Get network configuration by name"""
    return NETWORK_REGISTRY.get(network_name.lower())

def get_available_networks() -> list[str]:
    """Get list of available network names"""
    return list(NETWORK_REGISTRY.keys())

def get_network_display_names() -> dict[str, str]:
    """Get display names for all networks"""
    return {key: config.display_name for key, config in NETWORK_REGISTRY.items()}

__all__ = [
    'NetworkConfig',
    'Field',
    'ConditionalField',
    'BigOAdsConfig',
    'IronSourceConfig',
    'PangleConfig',
    'MintegralConfig',
    'InMobiConfig',
    'FyberConfig',
    'AppLovinConfig',
    'UnityConfig',
    'VungleConfig',
    'NETWORK_REGISTRY',
    'get_network_config',
    'get_available_networks',
    'get_network_display_names',
]

