"""
CHERENKOV reflector/introspect.py - memory self-audit ("truth about our own truth").

CHERENKOV's whole thesis is finding where a system's sources of truth disagree.
This module turns that lens *inward*: it audits the Reflector's accumulated
memory (verdicts + idioms) for self-contradiction and rot, so the learning loop
can't quietly poison itself - the reflexive answer to the reward-hacking / drift
risk that plagues autonomous QA.

Read-only. Depends only on the stable VerdictStore + core contracts.

Smells detected:
  • FLIP_FLOP             same finding was both ACCEPTed and REJECTed
  • CONFLICTING_IDIOMS    rival idioms compete for the same (endpoint, class)
  • STALE_BELIEF          high-confirmation idiom that has decayed toward zero
  • EPHEMERAL_SUPPRESSION  rejections keyed by a one-shot hypothesis_id, so a
                          fresh Skeptic run re-mints the id and the noise returns
"""
from __future__ import annotations

from collections import Counter, defaultdict
from enum import Enum

from pydantic import BaseModel, Field

from cherenkov.core.contracts import VerdictOutcome
from cherenkov.reflector.store import VerdictStore


class SmellType(str, Enum):
    FLIP_FLOP = "flip_flop"
    CONFLICTING_IDIOMS = "conflicting_idioms"
    STALE_BELIEF = "stale_belief"
    EPHEMERAL_SUPPRESSION = "ephemeral_suppression"


class MemorySmell(BaseModel):
    type: SmellType
    severity: str               # "low" | "medium" | "high"
    subject: str
    detail: str
    recommendation: str


class MemoryAudit(BaseModel):
    verdicts_examined: int
    idioms_examined: int
    smells: list[MemorySmell] = Field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.smells

    def render(self) -> str:
        head = (
            f"Reflector memory self-audit - {self.verdicts_examined} verdicts, "
            f"{self.idioms_examined} idioms examined"
        )
        if self.clean:
            return head + "\n  [ok] no self-contradictions found"
        lines = [head, f"  [!] {len(self.smells)} smell(s):"]
        for s in self.smells:
            lines.append(f"    [{s.severity.upper():6}] {s.type.value}: {s.subject}")
            lines.append(f"             {s.detail}")
            lines.append(f"             -> {s.recommendation}")
        return "\n".join(lines)


def audit_memory(
    store: VerdictStore,
    *,
    stale_decay: float = 0.3,
    stale_min_confirms: int = 3,
    scan_limit: int = 100_000,
) -> MemoryAudit:
    """Audit a VerdictStore for self-contradiction and rot. Pure read."""
    verdicts = store.get_recent_verdicts(limit=scan_limit)
    idioms = store.get_idioms(min_decay=0.0, limit=scan_limit)
    smells: list[MemorySmell] = []

    # 1) FLIP_FLOP - same (endpoint, class) signature both accepted and rejected
    by_sig: dict[tuple, set] = defaultdict(set)
    for v in verdicts:
        cls = v.divergence_class.value if v.divergence_class else None
        by_sig[(v.endpoint, cls)].add(v.outcome)
    for (endpoint, cls), outcomes in by_sig.items():
        if VerdictOutcome.ACCEPT in outcomes and VerdictOutcome.REJECT in outcomes:
            smells.append(MemorySmell(
                type=SmellType.FLIP_FLOP, severity="high",
                subject=f"{endpoint or '?'} / {cls or '?'}",
                detail="This signature was both ACCEPTed and REJECTed - the system's belief is unstable.",
                recommendation="Re-witness and have a senior set the authoritative verdict.",
            ))

    # 2) CONFLICTING_IDIOMS - rival patterns for the same (endpoint, class)
    groups: dict[tuple, list] = defaultdict(list)
    for i in idioms:
        groups[(i.endpoint, i.divergence_class.value)].append(i)
    for (endpoint, cls), grp in groups.items():
        patterns = {g.pattern for g in grp}
        if len(patterns) > 1:
            smells.append(MemorySmell(
                type=SmellType.CONFLICTING_IDIOMS, severity="medium",
                subject=f"{endpoint or '*'} / {cls}",
                detail=f"{len(patterns)} distinct idiom patterns compete for the same context.",
                recommendation="Merge or rank; keep the highest confirm_count, retire the rest.",
            ))

    # 3) STALE_BELIEF - strongly-confirmed idiom that has decayed toward zero
    for i in idioms:
        if i.confirm_count >= stale_min_confirms and i.decay_score < stale_decay:
            smells.append(MemorySmell(
                type=SmellType.STALE_BELIEF, severity="low",
                subject=i.pattern[:60],
                detail=f"confirmed {i.confirm_count}x but decayed to {i.decay_score:.2f} - possibly obsolete.",
                recommendation="Re-validate against current behaviour; retire if no longer true.",
            ))

    # 4) EPHEMERAL_SUPPRESSION - rejections that can never fire again
    id_counts = Counter(v.hypothesis_id for v in verdicts)
    ephemeral = [
        v for v in verdicts
        if v.outcome == VerdictOutcome.REJECT and id_counts[v.hypothesis_id] == 1
    ]
    if ephemeral:
        smells.append(MemorySmell(
            type=SmellType.EPHEMERAL_SUPPRESSION, severity="high",
            subject=f"{len(ephemeral)} rejection(s)",
            detail="Rejections are keyed by a one-shot hypothesis_id; a fresh Skeptic run "
                   "re-mints the id, so this suppressed noise will resurface.",
            recommendation="Suppress by a semantic fingerprint "
                           "(divergence_class + endpoint + normalized claims), not hypothesis_id.",
        ))

    return MemoryAudit(
        verdicts_examined=len(verdicts),
        idioms_examined=len(idioms),
        smells=smells,
    )
