"""Plugin discovery, loading, and lifecycle management."""

import importlib
import inspect
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ...core import get_logger
from ...core.paths import get_plugins_dir
from .api import MadracPlugin, PluginAPI

logger = get_logger("plugins.manager")


class PluginState:
    DISABLED = "disabled"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


@dataclass
class PluginHandle:
    name: str
    version: str
    api_version: int
    module_name: str
    state: str = PluginState.LOADED
    instance: Optional[MadracPlugin] = None
    api: Optional[PluginAPI] = None
    error: Optional[str] = None


class PluginManager:
    """Discovers, loads, initializes, and shuts down plugins.

    Usage:
        mgr = PluginManager()
        mgr.discover_all()
        mgr.init_all()
        ...
        mgr.shutdown_all()
    """

    def __init__(self, search_paths: Optional[List[Path]] = None) -> None:
        self._lock = threading.Lock()
        self._plugins: Dict[str, PluginHandle] = {}
        self._search_paths: List[Path] = list(search_paths or [get_plugins_dir()])
        self._stage_registrations: List[Dict[str, Any]] = []
        self._discovered = False

    # ---- discovery ----

    def discover_all(self) -> List[PluginHandle]:
        """Scan search paths for plugins, return list of handles."""
        with self._lock:
            self._plugins.clear()
            self._stage_registrations.clear()

            for base_path in self._search_paths:
                if not base_path.exists():
                    continue
                # Look for directories containing plugin modules
                for entry in sorted(base_path.iterdir()):
                    if not entry.is_dir():
                        continue
                    plugin_file = entry / "__init__.py"
                    if not plugin_file.exists():
                        # Try plugin_name.py
                        plugin_file = entry / f"{entry.name}.py"
                    if not plugin_file.exists():
                        continue
                    self._try_load_plugin(entry, plugin_file)

            self._discovered = True
            return list(self._plugins.values())

    def _try_load_plugin(self, entry: Path, plugin_file: Path) -> None:
        """Try to load a single plugin. On failure, log and continue."""
        module_name = entry.name
        try:
            # Add parent to sys.path and import
            parent = str(entry.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)

            spec = importlib.util.spec_from_file_location(module_name, str(plugin_file))
            if spec is None or spec.loader is None:
                logger.warning("Plugin '%s': could not load spec", module_name)
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Find MadracPlugin subclass
            plugin_class = self._find_plugin_class(mod)
            if plugin_class is None:
                logger.warning("Plugin '%s': no MadracPlugin subclass found", module_name)
                return

            instance = plugin_class()
            handle = PluginHandle(
                name=instance.name or module_name,
                version=instance.version,
                api_version=getattr(instance, "api_version", 1),
                module_name=module_name,
                state=PluginState.LOADED,
                instance=instance,
            )
            self._plugins[handle.name] = handle
            logger.info("Plugin discovered: %s v%s", handle.name, handle.version)

        except Exception as e:
            logger.exception("Plugin '%s' load failed: %s", module_name, e)
            self._plugins[module_name] = PluginHandle(
                name=module_name, version="?", api_version=0,
                module_name=module_name,
                state=PluginState.FAILED, error=str(e),
            )

    @staticmethod
    def _find_plugin_class(module: Any) -> Optional[Type[MadracPlugin]]:
        """Find the MadracPlugin subclass in a module."""
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, MadracPlugin) and obj is not MadracPlugin:
                return obj
        return None

    # ---- initialization ----

    def init_all(self) -> None:
        """Call initialize() on all discovered plugins. Errors are isolated."""
        with self._lock:
            for handle in self._plugins.values():
                if handle.state != PluginState.LOADED:
                    continue
                self._init_one(handle)

    def _init_one(self, handle: PluginHandle) -> None:
        """Initialize a single plugin with isolated error handling."""
        try:
            api = PluginAPI(handle.name, handle.version)
            handle.instance.initialize(api)
            handle.state = PluginState.INITIALIZED
            handle.api = api
            # Collect stage registrations
            for reg in api.get_registered_stages():
                self._stage_registrations.append({
                    "name": reg["name"],
                    "class": reg["class"],
                    "plugin": handle.name,
                })
            logger.info("Plugin initialized: %s", handle.name)
        except Exception as e:
            logger.exception("Plugin '%s' initialize() failed: %s", handle.name, e)
            handle.state = PluginState.FAILED
            handle.error = str(e)

    # ---- shutdown ----

    def shutdown_all(self) -> None:
        """Call shutdown() on all initialized plugins. Errors are isolated."""
        with self._lock:
            for handle in self._plugins.values():
                if handle.state not in (PluginState.INITIALIZED, PluginState.FAILED):
                    continue
                try:
                    if handle.instance:
                        handle.instance.shutdown()
                    handle.state = PluginState.SHUTDOWN
                except Exception as e:
                    logger.exception("Plugin '%s' shutdown() failed: %s", handle.name, e)

    # ---- query ----

    def get_plugins(self) -> Dict[str, PluginHandle]:
        with self._lock:
            return dict(self._plugins)

    def get_stage_registrations(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._stage_registrations)

    def get_plugin(self, name: str) -> Optional[PluginHandle]:
        with self._lock:
            return self._plugins.get(name)

    def is_failed(self, name: str) -> bool:
        handle = self.get_plugin(name)
        return handle is not None and handle.state == PluginState.FAILED
