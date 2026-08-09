"""Plugin SDK base classes for CHERENKOV-QA."""

class CustomSourceAdapter:
    """Base class for custom source adapters."""
    def __init__(self, source: str):
        self.source = source
        
    def iter_operations(self):
        raise NotImplementedError("Plugins must implement iter_operations")

class CustomReporter:
    """Base class for custom reporters."""
    def report(self, results: list):
        raise NotImplementedError("Plugins must implement report")

class CustomHealer:
    """Base class for custom healers."""
    def analyze_failure(self, failure: dict):
        raise NotImplementedError("Plugins must implement analyze_failure")
