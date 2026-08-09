"""Reference plugin for checking HIPAA compliance rules."""
import logging

_log = logging.getLogger("HIPAA_PLUGIN")

def on_divergence_detected(divergence: dict) -> None:
    """Hook invoked when a divergence is detected."""
    # Look for unencrypted or exposed PHI in the divergence
    details = str(divergence.get("details", "")).lower()
    if "ssn" in details or "patient_id" in details:
        _log.warning("[HIPAA] Potential PHI exposure detected in divergence: %s", divergence.get("id"))

def on_scenario_generated(scenario: dict) -> None:
    """Hook invoked when a test scenario is generated."""
    # Custom logic could be injected here
    pass
