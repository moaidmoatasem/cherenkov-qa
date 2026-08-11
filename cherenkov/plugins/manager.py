"""Plugin Manager for CHERENKOV-QA."""
import importlib.metadata
import logging
from typing import Any, Callable, Dict, List

_log = logging.getLogger("PLUGIN_MANAGER")

class PluginManager:
    """Discovers and loads third-party plugins via entry points."""

    def __init__(self, entry_point_group: str = "cherenkov.plugin"):
        self.entry_point_group = entry_point_group
        self.plugins: Dict[str, Any] = {}
        self.hooks: Dict[str, List[Callable]] = {
            "on_scenario_generated": [],
            "on_divergence_detected": [],
            "on_report_ready": []
        }
        self.load_plugins()

    def load_plugins(self) -> None:
        """Load all plugins registered under the entry point group."""
        # The `group=` keyword landed in 3.10 and pyproject sets
        # requires-python = ">=3.10", so the old
        # `entry_points().get(group, [])` fallback was unreachable — and it was
        # the source of the only type error in this module, because the 3.10+
        # return type is EntryPoints rather than a dict.
        eps = importlib.metadata.entry_points(group=self.entry_point_group)

        for ep in eps:
            try:
                plugin_module = ep.load()
                self.plugins[ep.name] = plugin_module
                self._register_hooks(plugin_module)
                _log.info("Loaded plugin: %s", ep.name)
            except Exception as e:
                _log.error("Failed to load plugin %s: %s", ep.name, e)

    def _register_hooks(self, plugin_module: Any) -> None:
        """Register hooks implemented by a plugin."""
        for hook_name in self.hooks.keys():
            if hasattr(plugin_module, hook_name):
                func = getattr(plugin_module, hook_name)
                if callable(func):
                    self.hooks[hook_name].append(func)

    def dispatch(self, hook_name: str, *args, **kwargs) -> None:
        """Dispatch a hook to all registered plugins."""
        if hook_name not in self.hooks:
            return
        
        for hook_func in self.hooks[hook_name]:
            try:
                hook_func(*args, **kwargs)
            except Exception as e:
                _log.error("Error executing hook %s: %s", hook_name, e)

    def list_plugins(self) -> List[str]:
        """Return a list of loaded plugin names."""
        return list(self.plugins.keys())
