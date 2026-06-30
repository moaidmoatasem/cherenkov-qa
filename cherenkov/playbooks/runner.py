"""PlaybookRunner — evaluates a Playbook's actions against a live API response."""

from __future__ import annotations

from typing import Any

from cherenkov.playbooks.models import Playbook, PlaybookFinding


class PlaybookRunner:
    """Applies a single Playbook's action rules to an observed API response and
    returns any findings raised."""

    def run(
        self,
        playbook: Playbook,
        *,
        endpoint: str,
        method: str,
        status_code: int | None = None,
        response_headers: dict[str, str] | None = None,
        response_body: Any = None,
        request_headers: dict[str, str] | None = None,
    ) -> list[PlaybookFinding]:
        findings: list[PlaybookFinding] = []
        response_headers = {k.lower(): v for k, v in (response_headers or {}).items()}
        request_headers = {k.lower(): v for k, v in (request_headers or {}).items()}
        method = method.upper()

        findings.extend(self._check_required_headers(playbook, endpoint, method, request_headers))
        findings.extend(self._check_expected_status(playbook, endpoint, method, status_code))
        findings.extend(
            self._check_forbidden_fields(playbook, endpoint, method, response_body)
        )
        findings.extend(
            self._check_required_fields(playbook, endpoint, method, response_body)
        )

        return findings

    # ------------------------------------------------------------------
    # Action evaluators
    # ------------------------------------------------------------------

    def _check_required_headers(
        self,
        pb: Playbook,
        endpoint: str,
        method: str,
        request_headers: dict[str, str],
    ) -> list[PlaybookFinding]:
        findings = []
        for header in pb.required_headers:
            if header.lower() not in request_headers:
                findings.append(
                    PlaybookFinding(
                        playbook_name=pb.name,
                        endpoint=endpoint,
                        method=method,
                        level=pb.severity,
                        message=f"Required header '{header}' missing from request",
                    )
                )
        return findings

    def _check_expected_status(
        self,
        pb: Playbook,
        endpoint: str,
        method: str,
        status_code: int | None,
    ) -> list[PlaybookFinding]:
        if not pb.expected_status or status_code is None:
            return []
        if status_code not in pb.expected_status:
            return [
                PlaybookFinding(
                    playbook_name=pb.name,
                    endpoint=endpoint,
                    method=method,
                    level=pb.severity,
                    message=(
                        f"Status {status_code} not in expected "
                        f"{pb.expected_status}"
                    ),
                )
            ]
        return []

    def _check_forbidden_fields(
        self,
        pb: Playbook,
        endpoint: str,
        method: str,
        body: Any,
    ) -> list[PlaybookFinding]:
        if not pb.forbidden_response_fields or not isinstance(body, dict):
            return []
        findings = []
        for field in pb.forbidden_response_fields:
            if self._field_present(body, field):
                findings.append(
                    PlaybookFinding(
                        playbook_name=pb.name,
                        endpoint=endpoint,
                        method=method,
                        level="error",
                        message=f"Forbidden field '{field}' found in response body",
                    )
                )
        return findings

    def _check_required_fields(
        self,
        pb: Playbook,
        endpoint: str,
        method: str,
        body: Any,
    ) -> list[PlaybookFinding]:
        if not pb.required_response_fields:
            return []
        if not isinstance(body, dict):
            return [
                PlaybookFinding(
                    playbook_name=pb.name,
                    endpoint=endpoint,
                    method=method,
                    level=pb.severity,
                    message="Expected JSON object response but body is not a dict",
                )
            ]
        findings = []
        for field in pb.required_response_fields:
            if not self._field_present(body, field):
                findings.append(
                    PlaybookFinding(
                        playbook_name=pb.name,
                        endpoint=endpoint,
                        method=method,
                        level=pb.severity,
                        message=f"Required field '{field}' missing from response body",
                    )
                )
        return findings

    @staticmethod
    def _field_present(body: dict, field: str) -> bool:
        """Check a dot-notation field path, e.g. 'user.password'."""
        parts = field.split(".", 1)
        if parts[0] not in body:
            return False
        if len(parts) == 1:
            return True
        sub = body[parts[0]]
        return isinstance(sub, dict) and PlaybookRunner._field_present(sub, parts[1])
