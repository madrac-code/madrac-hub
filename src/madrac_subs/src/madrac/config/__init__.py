"""
Configuration subsystem for MADRAC-SUBS v3.

Provides versioned, validated, TOML-persisted configuration
with migration support from v2 JSON configs.
"""

from .defaults import DEFAULTS, CONFIG_VERSION
from .schema import validate_config, merge_with_defaults, migrate_v2_to_v3
from .manager import (
    ConfigManager,
    get_config_manager,
    get_config,
    set_config,
)

__all__ = [
    "DEFAULTS",
    "CONFIG_VERSION",
    "validate_config",
    "merge_with_defaults",
    "migrate_v2_to_v3",
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "set_config",
]
