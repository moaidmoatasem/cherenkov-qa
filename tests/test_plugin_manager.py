import pytest
from cherenkov.plugins.manager import PluginManager

def test_plugin_manager_initialization():
    manager = PluginManager(entry_point_group="cherenkov.plugin.test")
    assert isinstance(manager.plugins, dict)
    assert "on_scenario_generated" in manager.hooks

def test_plugin_dispatch_no_error_for_unknown_hook():
    manager = PluginManager(entry_point_group="cherenkov.plugin.test")
    # Should not raise an error
    manager.dispatch("unknown_hook", data={})

class DummyPlugin:
    @staticmethod
    def on_scenario_generated(scenario):
        scenario["flag"] = True

def test_plugin_register_hooks():
    manager = PluginManager(entry_point_group="cherenkov.plugin.test")
    manager._register_hooks(DummyPlugin)
    
    assert len(manager.hooks["on_scenario_generated"]) == 1
    
    # Test dispatch
    scenario = {"flag": False}
    manager.dispatch("on_scenario_generated", scenario)
    assert scenario["flag"] is True
