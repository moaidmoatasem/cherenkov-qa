"""AI Model Routing.

Consolidates routing decisions across the stack to ensure consistent model selection based on tiers (small vs deep vs vision) and configured defaults in settings.
"""

from cherenkov.core.settings import get_settings


def get_model_for_task(task_type: str = "small") -> str:
    """Return the configured model name for a specific task complexity tier."""
    settings = get_settings()
    
    if task_type == "vision":
        return settings.TIER_VISION_MODEL
    elif task_type == "deep":
        return settings.TIER_DEEP_MODEL
    elif task_type == "small":
        return settings.TIER_SMALL_MODEL
    
    return settings.GEN_MODEL
