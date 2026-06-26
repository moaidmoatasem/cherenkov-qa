"""cherenkov/drift/snapshot.py — SpecSuiteSnapshot: baseline spine for drift detection.

The snapshot is the immutable record of a spec+suite pair at a point in time.
It lives outside any single run (loop-engineering STATE principle).
Detection is always a diff against this frozen baseline — never against memory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def canonicalize_spec(spec: dict[str, Any]) -> str:
    """Return a stable, whitespace-free JSON string for a spec dict.

    Sorts keys recursively so identical specs with different key order hash
    identically. This is the only normalization applied — we do not strip
    descriptions or examples, because those can carry semantic information
    relevant to schema_conformance scoring.
    """
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def spec_hash(spec: dict[str, Any]) -> str:
    return _sha256(canonicalize_spec(spec))


def suite_manifest_hash(suite: dict[str, Any]) -> str:
    """Hash the suite manifest (operation_id → test list mapping)."""
    canonical = json.dumps(suite, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(canonical)


@dataclass(frozen=True)
class SpecSuiteSnapshot:
    """Immutable baseline record — the spine that drift is measured against.

    snapshot_id: ISO-8601 timestamp key, unique per ledger entry.
    spec_hash:   sha256 of canonicalized spec.
    suite_hash:  sha256 of suite manifest.
    fingerprint: pre-computed Fingerprint for diff-without-rehydration.
    generation_profile: which model/prompt/profile produced the suite.
    created_at:  ISO-8601 wall-clock of creation.
    """

    snapshot_id: str
    spec_hash: str
    suite_hash: str
    fingerprint: "Fingerprint"  # noqa: F821  (imported at runtime)
    generation_profile: str
    created_at: str

    @classmethod
    def create(
        cls,
        spec: dict[str, Any],
        suite: dict[str, Any],
        generation_profile: str = "default",
    ) -> "SpecSuiteSnapshot":
        from cherenkov.drift.fingerprint import fingerprint_of

        now = datetime.now(timezone.utc)
        snapshot_id = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(
            snapshot_id=snapshot_id,
            spec_hash=spec_hash(spec),
            suite_hash=suite_manifest_hash(suite),
            fingerprint=fingerprint_of(spec, suite),
            generation_profile=generation_profile,
            created_at=snapshot_id,
        )

    def to_dict(self) -> dict[str, Any]:
        from cherenkov.drift.fingerprint import Fingerprint

        fp = self.fingerprint
        return {
            "snapshot_id": self.snapshot_id,
            "spec_hash": self.spec_hash,
            "suite_hash": self.suite_hash,
            "fingerprint": {
                "endpoint_coverage": fp.endpoint_coverage,
                "assertion_density": fp.assertion_density,
                "schema_conformance": fp.schema_conformance,
                "spec_completeness": fp.spec_completeness,
                "flake_rate": fp.flake_rate,
                "spec_version": fp.spec_version,
                "auth_scheme": fp.auth_scheme,
                "generation_profile": fp.generation_profile,
                "operation_set": sorted(fp.operation_set),
                "tag_set": sorted(fp.tag_set),
                "required_param_set": sorted(fp.required_param_set),
            },
            "generation_profile": self.generation_profile,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpecSuiteSnapshot":
        from cherenkov.drift.fingerprint import Fingerprint

        fp_data = data["fingerprint"]
        fp = Fingerprint(
            endpoint_coverage=fp_data["endpoint_coverage"],
            assertion_density=fp_data["assertion_density"],
            schema_conformance=fp_data["schema_conformance"],
            spec_completeness=fp_data["spec_completeness"],
            flake_rate=fp_data["flake_rate"],
            spec_version=fp_data["spec_version"],
            auth_scheme=fp_data["auth_scheme"],
            generation_profile=fp_data["generation_profile"],
            operation_set=frozenset(fp_data["operation_set"]),
            tag_set=frozenset(fp_data["tag_set"]),
            required_param_set=frozenset(fp_data["required_param_set"]),
        )
        return cls(
            snapshot_id=data["snapshot_id"],
            spec_hash=data["spec_hash"],
            suite_hash=data["suite_hash"],
            fingerprint=fp,
            generation_profile=data["generation_profile"],
            created_at=data["created_at"],
        )
