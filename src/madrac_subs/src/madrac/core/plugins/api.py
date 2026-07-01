"""Plugin API — frozen contract for MADRAC-SUBS v3 plugins.

This module defines the public API that plugins interact with.
Plugins must subclass MadracPlugin and implement initialize() and shutdown().
The PluginAPI object passed to initialize() is the only interface a plugin
has to the host application.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from ...core import get_logger, get_bus
from ...config import get_config, set_config

logger = get_logger("plugins.api")


class PluginAPI:
    """Restricted API surface exposed to plugins.

    Plugins access the host application ONLY through this object.
    Never pass internal objects (ConfigManager, EventBus, etc.) directly.
    """

    def __init__(self, plugin_name: str, plugin_version: str) -> None:
        self._name = plugin_name
        self._version = plugin_version
        self._stage_registry: List[Dict[str, Any]] = []

    def get_config(self, key: str, default: Any = None) -> Any:
        return get_config(key, default)

    def set_config(self, key: str, value: Any) -> None:
        set_config(key, value)

    def get_logger(self, name: str) -> Any:
        return get_logger(f"plugin.{self._name}.{name}")

    def emit_event(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        bus = get_bus()
        bus.emit(f"plugin.{self._name}.{event}", data)

    def register_stage(self, name: str, stage_class: Type) -> None:
        """Register a pipeline stage.

        Args:
            name: Unique stage name (e.g. 'ocr', 'tts').
            stage_class: A class that inherits from PipelineStage.
        """
        self._stage_registry.append({"name": name, "class": stage_class})
        logger.info("Plugin '%s' registered stage '%s'", self._name, name)

    def get_registered_stages(self) -> List[Dict[str, Any]]:
        return list(self._stage_registry)


class MadracPlugin:
    """Base class for all MADRAC-SUBS plugins.

    Subclasses MUST set name and version as class attributes.

    Lifecycle:
        1. PluginManager discovers and imports the module
        2. __init__() is called (no host access yet)
        3. initialize(api) is called — plugin registers stages, configures
        4. shutdown() is called on app exit — plugin releases resources

    If initialize() raises, the plugin is marked FAILED and skipped.
    shutdown() is called even if initialize() failed.
    """

    name: str = ""
    version: str = "0.0.0"
    api_version: int = 1

    def __init__(self) -> None:
        if not self.name:
            raise ValueError("Plugin must define 'name'")

    def initialize(self, api: PluginAPI) -> None:
        """Called after discovery. Plugin registers stages and configures itself.

        Args:
            api: PluginAPI — the ONLY way to interact with the host.
        """

    def shutdown(self) -> None:
        """Called during app shutdown. Release all resources here."""
