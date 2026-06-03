"""
CHERENKOV divergence/explorer.py — E10-1 Explorer.

Crawls a live app/API and surfaces anomalies (5xx, unexpected 4xx, slow
responses, JS/console errors, visual breaks) as ExplorerFindings, then converts
them into Skeptic-shaped DivergenceHypotheses so the rest of the divergence
engine can reason about them.

Design constraints:
  - Local-first / zero-dependency default: the HTTP crawl uses `requests`
    (already a project dependency). Browser-driven UI crawling (JS errors,
    visual breaks) is OPTIONAL and injected via a `ui_probe` callable, so the
    Explorer is fully unit-testable with no network and no browser installed.
  - The Explorer observes; it does not judge. Findings become *hypotheses* the
    Skeptic/Witness can confirm or reject — never auto-confirmed defects.
"""
from __future__ import annotations

import uuid
from typing import Callable, Iterable
from urllib.parse import urljoin

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    ExplorerFinding,
    ExplorerFindingKind,
    Severity,
)
from cherenkov.core.errors import get_logger

# A UI probe returns a list of (kind, detail, evidence) tuples for a URL.
# It is supplied by the caller (e.g. a Playwright-backed crawler) so this module
# never hard-depends on a browser. Returns JS_ERROR / VISUAL_BREAK findings.
UiProbe = Callable[[str], list[tuple[ExplorerFindingKind, str, str]]]

# An HTTP probe issues one request and returns (status, latency_ms, body_excerpt).
# Defaults to a `requests`-backed probe; overridable for tests.
HttpProbe = Callable[[str, str], tuple[int | None, int, str]]


def _default_http_probe(url: str, method: str) -> tuple[int | None, int, str]:
    """Issue a single request with a short budget. Never raises."""
    import time

    try:
        import requests
    except Exception:  # pragma: no cover - requests is a project dep
        return None, 0, "requests unavailable"

    t0 = time.time()
    try:
        resp = requests.request(method, url, timeout=10, allow_redirects=True)
        dt = int((time.time() - t0) * 1000)
        body = ""
        try:
            body = resp.text[:500]
        except Exception:
            body = ""
        return resp.status_code, dt, body
    except requests.exceptions.RequestException as e:
        dt = int((time.time() - t0) * 1000)
        return None, dt, str(e)[:500]


class Explorer:
    """Crawls live surfaces and emits anomalies the Skeptic can chase.

    Typical use:
        explorer = Explorer(base_url="http://localhost:8000")
        findings = explorer.crawl(paths=["/", "/pets", "/orders/999"])
        hypotheses = explorer.to_hypotheses(findings)   # feed the Skeptic
    """

    def __init__(
        self,
        base_url: str = "",
        run_id: str | None = None,
        http_probe: HttpProbe | None = None,
        ui_probe: UiProbe | None = None,
        slow_ms: int = 2000,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.run_id = run_id
        self.log = get_logger("EXPLORER", run_id)
        self._http_probe = http_probe or _default_http_probe
        self._ui_probe = ui_probe
        self.slow_ms = slow_ms

    # ── crawl ──────────────────────────────────────────────────────────────

    def crawl(
        self,
        paths: Iterable[str],
        method: str = "GET",
        expected_status: int | None = None,
    ) -> list[ExplorerFinding]:
        """Crawl each path and return findings for anything anomalous.

        Args:
            paths: route paths (joined onto base_url) or absolute URLs.
            method: HTTP verb to probe with.
            expected_status: if set, any other status is an unexpected-status
                finding; otherwise only 5xx / 4xx / slow / unreachable surface.
        """
        findings: list[ExplorerFinding] = []
        for path in paths:
            url = self._resolve(path)
            self.log.info("probing", url=url, method=method)
            status, latency_ms, body = self._http_probe(url, method)
            findings.extend(
                self._classify_http(url, method, status, latency_ms, body, expected_status)
            )
            if self._ui_probe is not None and method.upper() == "GET":
                findings.extend(self._run_ui_probe(url))
        self.log.info("crawl complete", probed=len(list(paths)) if hasattr(paths, "__len__") else -1,
                      findings=len(findings))
        return findings

    def _resolve(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not self.base_url:
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _classify_http(
        self,
        url: str,
        method: str,
        status: int | None,
        latency_ms: int,
        body: str,
        expected_status: int | None,
    ) -> list[ExplorerFinding]:
        out: list[ExplorerFinding] = []

        if status is None:
            out.append(self._finding(
                ExplorerFindingKind.UNREACHABLE, url, method, None, latency_ms,
                detail="No response (connection refused/timeout).",
                evidence=body, severity=Severity.HIGH,
            ))
            return out

        if status >= 500:
            out.append(self._finding(
                ExplorerFindingKind.SERVER_ERROR, url, method, status, latency_ms,
                detail=f"Server returned {status}.",
                evidence=body, severity=Severity.CRITICAL,
            ))
        elif expected_status is not None and status != expected_status:
            sev = Severity.HIGH if status >= 400 else Severity.MEDIUM
            kind = (ExplorerFindingKind.CLIENT_ERROR if 400 <= status < 500
                    else ExplorerFindingKind.SERVER_ERROR)
            out.append(self._finding(
                kind, url, method, status, latency_ms,
                detail=f"Expected {expected_status}, got {status}.",
                evidence=body, severity=sev,
            ))
        elif 400 <= status < 500 and expected_status is None:
            out.append(self._finding(
                ExplorerFindingKind.CLIENT_ERROR, url, method, status, latency_ms,
                detail=f"Client error {status} on a crawled route.",
                evidence=body, severity=Severity.MEDIUM,
            ))

        if latency_ms >= self.slow_ms:
            out.append(self._finding(
                ExplorerFindingKind.SLOW_RESPONSE, url, method, status, latency_ms,
                detail=f"Response took {latency_ms}ms (budget {self.slow_ms}ms).",
                evidence="", severity=Severity.LOW,
            ))
        return out

    def _run_ui_probe(self, url: str) -> list[ExplorerFinding]:
        out: list[ExplorerFinding] = []
        try:
            for kind, detail, evidence in self._ui_probe(url):  # type: ignore[misc]
                sev = (Severity.HIGH if kind == ExplorerFindingKind.JS_ERROR
                       else Severity.MEDIUM)
                out.append(self._finding(kind, url, "GET", None, 0, detail, evidence, sev))
        except Exception as e:  # a probe must never crash the crawl
            self.log.warning("ui_probe failed", url=url, error=str(e))
        return out

    @staticmethod
    def _finding(
        kind: ExplorerFindingKind,
        url: str,
        method: str,
        status: int | None,
        latency_ms: int,
        detail: str,
        evidence: str,
        severity: Severity,
    ) -> ExplorerFinding:
        return ExplorerFinding(
            id=str(uuid.uuid4()),
            kind=kind,
            url=url,
            method=method,
            status=status,
            latency_ms=latency_ms,
            detail=detail,
            evidence=evidence,
            severity=severity,
        )

    # ── feed the Skeptic ─────────────────────────────────────────────────────

    def to_hypotheses(self, findings: list[ExplorerFinding]) -> list[DivergenceHypothesis]:
        """Convert observed findings into Skeptic-shaped hypotheses.

        A 5xx/unreachable maps to D2 (code↔prod: source claims success, prod
        fails); an unexpected 4xx/missing route maps to D5 (spec↔prod: spec
        defines it, prod doesn't behave). JS/visual breaks map to D3 (ui↔spec).
        These are *unconfirmed* — the Witness still has to reproduce them.
        """
        hypotheses: list[DivergenceHypothesis] = []
        for f in findings:
            dclass, claim_a, claim_b = self._map_class(f)
            hypotheses.append(DivergenceHypothesis(
                id=str(uuid.uuid4()),
                divergence_class=dclass,
                claim_a=claim_a,
                claim_b=claim_b,
                predicted_evidence=f.detail or f.kind.value,
                severity=f.severity,
                endpoint=f"{f.method.upper()} {f.url}",
                repro_steps=[
                    f"Send {f.method.upper()} {f.url}",
                    f"Observe: {f.detail or f.kind.value}",
                ],
            ))
        return hypotheses

    @staticmethod
    def _map_class(f: ExplorerFinding) -> tuple[DivergenceClass, str, str]:
        if f.kind in (ExplorerFindingKind.SERVER_ERROR, ExplorerFindingKind.UNREACHABLE,
                      ExplorerFindingKind.SLOW_RESPONSE):
            return (
                DivergenceClass.D2_CODE_PROD,
                "Source code intends this route to succeed.",
                f"Production returns {f.status or 'no response'} ({f.kind.value}).",
            )
        if f.kind == ExplorerFindingKind.CLIENT_ERROR:
            return (
                DivergenceClass.D5_SPEC_PROD,
                "A reachable route was expected here.",
                f"Production responds {f.status} ({f.kind.value}).",
            )
        # JS_ERROR / VISUAL_BREAK
        return (
            DivergenceClass.D3_UI_SPEC,
            "UI is expected to render/behave per spec.",
            f"UI surface anomaly: {f.detail or f.kind.value}.",
        )
