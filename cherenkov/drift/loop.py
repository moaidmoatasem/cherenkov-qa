"""cherenkov/drift/loop.py — Autonomy gate (L1/L2/L3) + maker/checker orchestration.

Phase 12 ships L1-only (report + no auto-mutation). L2/L3 stubs are present
so the interface is stable but they escalate rather than act.

Phased autonomy graduates per drift-kind, not globally:
  L1 — report only. Never mutates the suite. Default for everything.
  L2 — maker proposes a diff, checker verifies, human approves before write.
       Default scope: NEW_OP_UNTESTED, ADDED_OPTIONAL_PARAM.
  L3 — reconcile + commit automatically with full-context audit trail.
       Only kinds that earned a clean L2 track record (Phase 13+).

Anything FAIL-severity always escalates to human — the loop never auto-resolves
a breaking change.

Cost rule: the LLM fires only on confirmed-drift reconciliation, only for the
drifted operations, never the whole suite. (§7)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from cherenkov.drift.detect import DriftKind, DriftFinding
from cherenkov.drift.reconcile import DriftReport, DriftVerdict, SEVERITY


class AutonomyLevel(str, Enum):
    L1_REPORT    = "L1"   # detect + write DriftReport, never mutate
    L2_ASSISTED  = "L2"   # maker proposes, checker verifies, human approves
    L3_UNATTENDED = "L3"  # reconcile + commit automatically (Phase 13+)


# Kinds that are eligible for L2 by default (low-risk, reversible-feeling)
_L2_ALLOWLIST: frozenset[DriftKind] = frozenset({
    DriftKind.NEW_OP_UNTESTED,
    DriftKind.ADDED_OPTIONAL_PARAM,
})


@dataclass
class ReconciliationProposal:
    """A maker-generated proposal for a single drifted operation."""

    operation_id: str
    drift_kind: DriftKind
    action: str               # human-readable description of proposed change
    patch: dict[str, Any] = field(default_factory=dict)  # structured diff (Phase 13)
    verified: bool = False     # set True after checker pass


@dataclass
class LoopResult:
    """Output of one DriftLoop.run() invocation."""

    report: DriftReport
    level: AutonomyLevel
    proposals: list[ReconciliationProposal] = field(default_factory=list)
    escalations: list[DriftFinding] = field(default_factory=list)
    committed: bool = False
    audit_trail: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"autonomy={self.level.value}",
            f"committed={self.committed}",
            f"proposals={len(self.proposals)}",
            f"escalations={len(self.escalations)}",
            "",
            self.report.summary(),
        ]
        if self.escalations:
            lines.append("--- escalations (require human review) ---")
            for f in self.escalations:
                lines.append(f"  {f.kind.value}: {f.detail}")
        return "\n".join(lines)


class DriftLoop:
    """Maker/checker loop with phased autonomy gate.

    Usage (L1 — Phase 12 default):
        loop = DriftLoop(level=AutonomyLevel.L1_REPORT)
        result = loop.run(report)

    The maker_fn is called only at L2/L3 and only for non-FAIL findings.
    It receives a DriftFinding and must return a ReconciliationProposal.

    The checker_fn verifies proposals. It defaults to a stub that marks
    proposals as unverified (Phase 13 wires in CANDOR + banned_pattern_linter).

    The commit_fn writes approved proposals to disk. It is never called at L1.
    """

    def __init__(
        self,
        level: AutonomyLevel = AutonomyLevel.L1_REPORT,
        l2_allowlist: frozenset[DriftKind] | None = None,
        maker_fn: Callable[[DriftFinding], ReconciliationProposal] | None = None,
        checker_fn: Callable[[ReconciliationProposal], bool] | None = None,
        commit_fn: Callable[[list[ReconciliationProposal]], None] | None = None,
        approval_fn: Callable[[list[ReconciliationProposal]], bool] | None = None,
    ) -> None:
        self.level = level
        self.l2_allowlist = l2_allowlist if l2_allowlist is not None else _L2_ALLOWLIST
        self.maker_fn = maker_fn or self._default_maker
        self.checker_fn = checker_fn or self._default_checker
        self.commit_fn = commit_fn or self._default_commit
        self.approval_fn = approval_fn or self._default_approval

    def run(self, report: DriftReport) -> LoopResult:
        """Execute the autonomy gate for a DriftReport.

        L1: returns proposals=[], escalations=<all FAIL findings>, committed=False.
        L2: proposes for allowlisted kinds, escalates the rest, awaits approval.
        L3: propose + verify + commit automatically (stub — Phase 13+).
        """
        result = LoopResult(report=report, level=self.level)

        if not report.has_drift:
            result.audit_trail.append("no drift detected — nothing to do")
            return result

        # Partition findings by what can be handled at current autonomy level
        auto_findings: list[DriftFinding] = []
        escalate_findings: list[DriftFinding] = []

        for finding in report.findings:
            severity = SEVERITY[finding.kind]
            if severity == DriftVerdict.FAIL:
                # FAIL always escalates — the loop never auto-resolves breaking changes
                escalate_findings.append(finding)
            elif self.level == AutonomyLevel.L1_REPORT:
                escalate_findings.append(finding)
            elif finding.kind in self.l2_allowlist:
                auto_findings.append(finding)
            else:
                escalate_findings.append(finding)

        result.escalations = escalate_findings

        if escalate_findings:
            result.audit_trail.append(
                f"escalating {len(escalate_findings)} finding(s) to human review"
            )

        if self.level == AutonomyLevel.L1_REPORT or not auto_findings:
            return result

        # L2 / L3: invoke maker for each eligible finding
        proposals: list[ReconciliationProposal] = []
        for finding in auto_findings:
            try:
                proposal = self.maker_fn(finding)
                verified = self.checker_fn(proposal)
                proposal.verified = verified
                if verified:
                    proposals.append(proposal)
                    result.audit_trail.append(
                        f"maker proposed + checker verified: {finding.kind.value} "
                        f"for {finding.operation_id}"
                    )
                else:
                    result.escalations.append(finding)
                    result.audit_trail.append(
                        f"checker rejected proposal for {finding.operation_id} — escalating"
                    )
            except Exception as exc:
                result.escalations.append(finding)
                result.audit_trail.append(
                    f"maker error on {finding.operation_id}: {exc!s} — escalating"
                )

        result.proposals = proposals

        if self.level == AutonomyLevel.L2_ASSISTED and proposals:
            # Gate on human approval before writing
            approved = self.approval_fn(proposals)
            if approved:
                self.commit_fn(proposals)
                result.committed = True
                result.audit_trail.append(
                    f"human approved; committed {len(proposals)} proposal(s)"
                )
            else:
                result.audit_trail.append("human rejected proposals — no write")

        elif self.level == AutonomyLevel.L3_UNATTENDED and proposals:
            # L3: auto-commit with audit trail (Phase 13+ gating)
            self.commit_fn(proposals)
            result.committed = True
            result.audit_trail.append(
                f"L3 unattended: committed {len(proposals)} proposal(s)"
            )

        return result

    # ── default stubs (replaced by real implementations in Phase 13) ──────────

    @staticmethod
    def _default_maker(finding: DriftFinding) -> ReconciliationProposal:
        """Placeholder maker — returns a no-op proposal with a human-readable action."""
        action_map = {
            DriftKind.NEW_OP_UNTESTED: (
                f"Generate test skeleton for '{finding.operation_id}'"
            ),
            DriftKind.ADDED_OPTIONAL_PARAM: (
                f"Annotate '{finding.detail}' in existing tests for '{finding.operation_id}'"
            ),
            DriftKind.REMOVED_OP_STILL_TESTED: (
                f"Remove tests for deleted operation '{finding.operation_id}'"
            ),
        }
        action = action_map.get(finding.kind, f"Reconcile {finding.kind.value}")
        return ReconciliationProposal(
            operation_id=finding.operation_id,
            drift_kind=finding.kind,
            action=action,
        )

    @staticmethod
    def _default_checker(proposal: ReconciliationProposal) -> bool:
        """Stub checker — always returns False (Phase 13 wires CANDOR + linter)."""
        return False

    @staticmethod
    def _default_commit(proposals: list[ReconciliationProposal]) -> None:
        """Stub commit — no-op (Phase 13 wires actual suite write)."""

    @staticmethod
    def _default_approval(proposals: list[ReconciliationProposal]) -> bool:
        """Stub approval gate — always returns False (requires real human input)."""
        return False

    # ── Phase 13 factories ────────────────────────────────────────────────────

    @classmethod
    def with_real_maker(
        cls,
        spec: dict[str, Any],
        **kwargs: Any,
    ) -> "DriftLoop":
        """Return a DriftLoop wired with the schema-driven maker."""
        from cherenkov.drift.maker import make_proposal as _make

        return cls(maker_fn=lambda f: _make(f, spec), **kwargs)

    @classmethod
    def with_real_checker(cls, **kwargs: Any) -> "DriftLoop":
        """Return a DriftLoop wired with the banned-pattern checker."""
        from cherenkov.drift.checker import check_proposal

        return cls(checker_fn=check_proposal, **kwargs)

    @classmethod
    def l2_interactive(
        cls,
        spec: dict[str, Any],
        suite_path: "Path | None" = None,  # noqa: F821
        auto_approve: bool = False,
    ) -> "DriftLoop":
        """Full L2 loop: real maker + real checker + interactive (or auto) approval.

        Args:
            spec:         Current OpenAPI spec dict (for schema-driven maker).
            suite_path:   Path to the suite JSON file; passed to commit_fn.
                          If None, commit is a no-op (proposals are returned only).
            auto_approve: If True, bypass human confirmation (CI/scripted use).
        """
        from cherenkov.drift.maker import make_proposal as _make, patch_suite
        from cherenkov.drift.checker import check_proposal

        def _approval(proposals: list[ReconciliationProposal]) -> bool:
            if auto_approve:
                return True
            try:
                import click

                for p in proposals:
                    click.echo(f"\n  Proposal for '{p.operation_id}':")
                    click.echo(f"    action : {p.action}")
                    click.echo(f"    kind   : {p.drift_kind.value}")
                if not click.confirm(
                    f"\n  Approve {len(proposals)} proposal(s)?", default=False
                ):
                    return False
                return True
            except Exception:
                return False

        def _commit(proposals: list[ReconciliationProposal]) -> None:
            if suite_path is not None:
                patch_suite(proposals, suite_path)

        return cls(
            level=AutonomyLevel.L2_ASSISTED,
            maker_fn=lambda f: _make(f, spec),
            checker_fn=check_proposal,
            approval_fn=_approval,
            commit_fn=_commit,
        )
