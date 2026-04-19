"""Plugin discovery using importlib.metadata and entry_points.

This module provides dynamic plugin loading from installed packages.
"""

import importlib.metadata
import logging
from typing import Dict, List, Optional, Type, Any
from pathlib import Path

from .interfaces import (
    LLMProvider,
    MemoryBackend,
    ToolRegistry,
    Orchestrator,
    Observer,
    PluginInterface,
)

logger = logging.getLogger(__name__)


class PluginDiscovery:
    """Discover and load plugins using entry_points."""

    ENTRY_POINT_GROUPS = {
        "llm": "agentmind.plugins.llm",
        "memory": "agentmind.plugins.memory",
        "tools": "agentmind.plugins.tools",
        "orchestrator": "agentmind.plugins.orchestrator",
        "observer": "agentmind.plugins.observer",
    }

    def __init__(self):
        """Initialize plugin discovery."""
        self._discovered_plugins: Dict[str, Dict[str, Any]] = {
            "llm": {},
            "memory": {},
            "tools": {},
            "orchestrator": {},
            "observer": {},
        }
        self._loaded_plugins: Dict[str, Any] = {}

    def discover_all(self) -> Dict[str, List[str]]:
        """Discover all available plugins.

        Returns:
            Dict mapping plugin type to list of plugin names
        """
        results = {}

        for plugin_type, group_name in self.ENTRY_POINT_GROUPS.items():
            plugins = self.discover_by_type(plugin_type)
            results[plugin_type] = list(plugins.keys())
            logger.info(f"Discovered {len(plugins)} {plugin_type} plugins")

        return results

    def discover_by_type(self, plugin_type: str) -> Dict[str, Any]:
        """Discover plugins of a specific type.

        Args:
            plugin_type: Type of plugin (llm, memory, tools, orchestrator, observer)

        Returns:
            Dict mapping plugin name to entry point
        """
        if plugin_type not in self.ENTRY_POINT_GROUPS:
            logger.error(f"Unknown plugin type: {plugin_type}")
            return {}

        group_name = self.ENTRY_POINT_GROUPS[plugin_type]
        discovered = {}

        try:
            # Use importlib.metadata to discover entry points
            entry_points = importlib.metadata.entry_points()

            # Handle both old and new entry_points API
            if hasattr(entry_points, "select"):
                # Python 3.10+
                group_eps = entry_points.select(group=group_name)
            else:
                # Python 3.8-3.9
                group_eps = entry_points.get(group_name, [])

            for ep in group_eps:
                discovered[ep.name] = ep
                self._discovered_plugins[plugin_type][ep.name] = ep
                logger.debug(f"Discovered {plugin_type} plugin: {ep.name}")

        except Exception as e:
            logger.error(f"Error discovering {plugin_type} plugins: {e}")

        return discovered

    def load_plugin(self, plugin_type: str, plugin_name: str) -> Optional[Any]:
        """Load a specific plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Loaded plugin class or None
        """
        cache_key = f"{plugin_type}:{plugin_name}"

        # Return cached if already loaded
        if cache_key in self._loaded_plugins:
            return self._loaded_plugins[cache_key]

        # Discover if not already discovered
        if plugin_name not in self._discovered_plugins.get(plugin_type, {}):
            self.discover_by_type(plugin_type)

        # Get entry point
        entry_point = self._discovered_plugins.get(plugin_type, {}).get(plugin_name)
        if not entry_point:
            logger.error(f"Plugin not found: {plugin_type}:{plugin_name}")
            return None

        try:
            # Load the plugin class
            plugin_class = entry_point.load()
            self._loaded_plugins[cache_key] = plugin_class
            logger.info(f"Loaded plugin: {plugin_type}:{plugin_name}")
            return plugin_class

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_type}:{plugin_name}: {e}")
            return None

    def load_all_by_type(self, plugin_type: str) -> Dict[str, Any]:
        """Load all plugins of a specific type.

        Args:
            plugin_type: Type of plugin

        Returns:
            Dict mapping plugin name to loaded class
        """
        discovered = self.discover_by_type(plugin_type)
        loaded = {}

        for plugin_name in discovered.keys():
            plugin_class = self.load_plugin(plugin_type, plugin_name)
            if plugin_class:
                loaded[plugin_name] = plugin_class

        return loaded

    def get_plugin_info(self, plugin_type: str, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Plugin information dict or None
        """
        entry_point = self._discovered_plugins.get(plugin_type, {}).get(plugin_name)
        if not entry_point:
            return None

        try:
            # Try to get distribution info
            dist = importlib.metadata.distribution(entry_point.value.split(":")[0])
            return {
                "name": plugin_name,
                "type": plugin_type,
                "module": entry_point.value,
                "distribution": dist.name,
                "version": dist.version,
                "metadata": dict(dist.metadata),
            }
        except Exception as e:
            logger.warning(f"Could not get full info for {plugin_name}: {e}")
            return {
                "name": plugin_name,
                "type": plugin_type,
                "module": entry_point.value,
            }

    def list_installed_plugins(self) -> List[Dict[str, Any]]:
        """List all installed AgentMind plugins.

        Returns:
            List of plugin info dicts
        """
        all_plugins = []

        for plugin_type in self.ENTRY_POINT_GROUPS.keys():
            discovered = self.discover_by_type(plugin_type)
            for plugin_name in discovered.keys():
                info = self.get_plugin_info(plugin_type, plugin_name)
                if info:
                    all_plugins.append(info)

        return all_plugins


# Global discovery instance
_global_discovery = PluginDiscovery()


def discover_plugins() -> Dict[str, List[str]]:
    """Discover all available plugins.

    Returns:
        Dict mapping plugin type to list of plugin names
    """
    return _global_discovery.discover_all()


def load_plugin(plugin_type: str, plugin_name: str) -> Optional[Any]:
    """Load a specific plugin.

    Args:
        plugin_type: Type of plugin
        plugin_name: Name of plugin

    Returns:
        Loaded plugin class or None
    """
    return _global_discovery.load_plugin(plugin_type, plugin_name)


def list_plugins() -> List[Dict[str, Any]]:
    """List all installed plugins.

    Returns:
        List of plugin info dicts
    """
    return _global_discovery.list_installed_plugins()
