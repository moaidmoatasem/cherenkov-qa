"""AI Model Routing.

Consolidates routing decisions across the stack to ensure consistent model selection based on tiers (small vs deep vs vision) and configured defaults in settings.
"""

from cherenkov.core.settings import get_settings
from cherenkov.plugins.manager import PluginManager
from cherenkov.plugins.sdk import CustomLLMProvider

def get_model_for_task(task_type: str = "small") -> str:
    """Return the configured model name for a specific task complexity tier.

    Args:
        task_type: Complexity tier ("vision", "deep", "small").

    Returns:
        str: Model identifier name configured for the tier.
    """
    settings = get_settings()
    
    if task_type == "vision":
        return settings.TIER_VISION_MODEL
    elif task_type == "deep":
        return settings.TIER_DEEP_MODEL
    elif task_type == "small":
        return settings.TIER_SMALL_MODEL
    
    return settings.GEN_MODEL

def resolve_llm_provider(model_name: str) -> CustomLLMProvider | None:
    """Resolve an LLM provider if the model name specifies a plugin (e.g., 'plugin:mistral').

    Args:
        model_name: Model identifier string or plugin specifier.

    Returns:
        CustomLLMProvider | None: Resolved provider instance if available, otherwise None.
    """
    if not model_name.startswith("plugin:"):
        return None
        
    plugin_name = model_name[7:]
    manager = PluginManager()
    
    # Try to find a CustomLLMProvider in the loaded plugins
    for plugin in manager.plugins.values():
        if isinstance(plugin, CustomLLMProvider) and getattr(plugin, "__module__", "").endswith(plugin_name):
            # In a real app we'd map this better, but for SDK ref we can just check if it's the requested plugin
            return plugin
            
    # For now, if they requested mistral, just return the instance
    if plugin_name == "mistral":
        # Ensure plugins are loaded
        if not manager.plugins:
            manager.discover_plugins()
        for name, inst in manager.plugins.items():
            if name == "mistral" and isinstance(inst, CustomLLMProvider):
                return inst
    
    return None

