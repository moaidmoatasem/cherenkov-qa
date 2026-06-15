"""Spec Guardian daemon - continuous API drift monitoring."""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from cherenkov.spec_guardian.core import (
    DriftEvent,
    DriftReport,
    DriftSeverity,
)
from cherenkov.spec_guardian.detector import SpecDriftDetector
from cherenkov.spec_guardian.store import DriftStore


logger = logging.getLogger(__name__)


class SpecGuardianDaemon:
    """Daemon that continuously monitors API endpoints for spec drift."""
    
    def __init__(
        self,
        spec_path: str,
        base_url: str,
        check_interval: int = 60,
        endpoints: list[dict[str, Any]] | None = None,
        db_path: Path | None = None,
    ):
        """Initialize the daemon.
        
        Args:
            spec_path: Path to OpenAPI spec file
            base_url: Base URL of the API to monitor
            check_interval: Seconds between checks (default: 60)
            endpoints: List of endpoints to check, each with method and optional params
            db_path: Path to SQLite database (default: .cherenkov/drift.db)
        """
        self.spec_path = spec_path
        self.base_url = base_url.rstrip("/")
        self.check_interval = check_interval
        self.endpoints = endpoints or []
        self.detector = SpecDriftDetector(spec_path)
        self.store = DriftStore(db_path or DriftStore.DRIFT_DB)
        self.running = False
        self.session_start: datetime | None = None
        self.total_checks = 0
        self.compliant_checks = 0
        self.all_events: list[DriftEvent] = []
    
    def start(self) -> None:
        """Start the monitoring daemon."""
        self.running = True
        self.session_start = datetime.utcnow()
        
        # Handle shutdown signals
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(
            "Spec Guardian daemon started",
            extra={
                "spec_path": self.spec_path,
                "base_url": self.base_url,
                "check_interval": self.check_interval,
                "endpoints": len(self.endpoints),
            },
        )
        
        while self.running:
            try:
                self._run_check_cycle()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error("Error in check cycle", exc_info=True)
                time.sleep(self.check_interval)
    
    def stop(self) -> None:
        """Stop the monitoring daemon."""
        self.running = False
        logger.info("Spec Guardian daemon stopping")
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down")
        self.stop()
    
    def _run_check_cycle(self) -> None:
        """Run a single check cycle across all configured endpoints."""
        cycle_start = datetime.utcnow()
        cycle_events: list[DriftEvent] = []
        
        for endpoint_config in self.endpoints:
            try:
                events = self._check_endpoint(endpoint_config)
                cycle_events.extend(events)
                
                # Save each event immediately
                for event in events:
                    self.store.save_event(event)
                
                self.total_checks += 1
                if not events:
                    self.compliant_checks += 1
                
            except Exception as e:
                logger.error(
                    "Failed to check endpoint",
                    extra={"endpoint": endpoint_config, "error": str(e)},
                    exc_info=True,
                )
        
        # Generate and save report every cycle
        if cycle_events or self.total_checks > 0:
            report = DriftReport(
                spec_path=self.spec_path,
                events=self.all_events + cycle_events,
                start_time=self.session_start or cycle_start,
                end_time=datetime.utcnow(),
                total_checks=self.total_checks,
                compliant_checks=self.compliant_checks,
            )
            self.store.save_report(report)
            self.all_events.extend(cycle_events)
            
            # Log summary
            drift_rate = report.drift_rate
            if drift_rate > 0.1:
                logger.warning(
                    "High drift rate detected",
                    extra={
                        "drift_rate": drift_rate,
                        "events": len(cycle_events),
                        "critical": report.critical_count,
                    },
                )
            else:
                logger.info(
                    "Check cycle complete",
                    extra={
                        "drift_rate": drift_rate,
                        "events": len(cycle_events),
                        "total_checks": self.total_checks,
                    },
                )
    
    def _check_endpoint(self, endpoint_config: dict[str, Any]) -> list[DriftEvent]:
        """Check a single endpoint against the spec.
        
        Args:
            endpoint_config: Dict with 'method', 'path', and optional 'params', 'headers'
            
        Returns:
            List of drift events detected
        """
        method = endpoint_config.get("method", "GET").upper()
        path = endpoint_config["path"]
        params = endpoint_config.get("params", {})
        headers = endpoint_config.get("headers", {})
        
        url = f"{self.base_url}{path}"
        
        logger.debug(f"Checking {method} {url}")
        
        # Make the actual API call
        response = requests.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            timeout=30,
        )
        
        # Parse response body
        try:
            response_body = response.json() if response.content else None
        except Exception:
            response_body = None
        
        # Check against spec
        events = self.detector.check_response(
            endpoint=path,
            method=method,
            status_code=response.status_code,
            response_body=response_body,
            response_headers=dict(response.headers),
        )
        
        return events
    
    def run_once(self) -> DriftReport:
        """Run a single check cycle and return the report.
        
        Useful for testing or one-off checks.
        """
        self.session_start = datetime.utcnow()
        self._run_check_cycle()
        
        return DriftReport(
            spec_path=self.spec_path,
            events=self.all_events,
            start_time=self.session_start,
            end_time=datetime.utcnow(),
            total_checks=self.total_checks,
            compliant_checks=self.compliant_checks,
        )
