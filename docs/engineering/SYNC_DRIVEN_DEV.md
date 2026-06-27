# Sync Driven Development (SDD) — Token-Efficient Agent Methodology

**Status:** Active · **Date:** 2026-06-10
**Author:** Agent-0 / Owner
**Applies to:** All autonomous agents working on CHERENKOV-QA

---

## 1. The Problem

AI agents suffer from three structural inefficiencies:

| Problem | Cost | Manifestation |
|---------|------|---------------|
| **Amnesia** | Re-reading context every session | Same docs fetched, same bugs rediscovered, same decisions re-made |
| **Token waste** | Unstructured prompt construction | Full document dumps, redundant instructions, no relevance filtering |
| **No compounding** | Experience evaporates between sessions | Mistakes repeated, patterns never learned, no measurable improvement |

**SDD solves all three** by making *sync the contract*: agents MUST sync state before, during, and after every session.

---

## 2. The SDD Principle

> **Every agent action is synced to persistent storage in real-time. The sync is the source of truth — not the agent's ephemeral context.**

```
┌─────────────────────────────────────────────────────────┐
│                    SDD CYCLE                             │
│                                                         │
│  Before Session ──→ During Session ──→ After Session    │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ Load context │  │ Log findings  │  │ Compact logs │ │
│  │ Check budget │  │ Track tokens  │  │ Update exp.  │ │
│  │ Load exp.    │  │ Use compact   │  │ Close sess.  │ │
│  │ Start sess.  │  │ context only  │  │ Report delta │ │
│  └──────────────┘  └───────────────┘  └──────────────┘ │
│                                                         │
│  ▼ Next session continues from previous sync state      │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Token Optimization Strategy

### 3.1 Context Tiers
Instead of loading all docs, load only what you need:

| Tier | Token Budget | Contents | When |
|------|-------------|----------|------|
| **T1: Skeletal** | ~500 tokens | Project name, SSOT location, current phase | Every session |
| **T2: Focused** | ~2,000 tokens | Relevant memory files + 1 skill file | Task-specific |
| **T3: Full** | ~8,000 tokens | All docs referenced by PHASE_PLAN | Deep work / new areas |

**Rule:** Start at T1. Escalate to T2 only if task requires it. Never load T3 by default.

### 3.2 Pre-Computed Context
The `agent_memory/sync/context.json` file contains pre-computed context snippets for common task types. Use these instead of re-reading source documents.

Context snippets are computed from:
- Current phase status (from `docs/STATUS.md`)
- Active tracks (from `AGENTS.md`)
- Relevant ADRs (from `docs/adr/`)
- Known bugs (from `agent_memory/known-bugs.md`)

### 3.3 Token Budget
Every session has a **token budget** tracked in `agent_memory/sync/tokens.json`:

| Session Type | Budget | Hard Cap |
|-------------|--------|----------|
| Standard dev | 50,000 tokens | 100,000 tokens |
| Deep investigation | 100,000 tokens | 200,000 tokens |
| Quick fix | 20,000 tokens | 50,000 tokens |

When approaching 80% of budget, the agent MUST run compaction to free context.

### 3.4 Deduplication
- If the same context appears in 3+ consecutive sessions, promote it to `context.json` for automatic inclusion
- If a memory entry hasn't been read in 10 sessions, archive it
- Never include the same document twice in a single session

---

## 4. Experience Compounding

### 4.1 What Gets Recorded
Every meaningful agent action produces an **experience record**:

```json
{
  "id": "exp_20260610_001",
  "timestamp": "2026-06-10T10:30:00Z",
  "task": "Add K8s CRD validation",
  "action": "Decision: use Go validator instead of JSON Schema",
  "rationale": "Go validator gives better type safety with CRD structs",
  "outcome": "success",
  "token_cost": 12500,
  "patterns": ["k8s", "crd", "go-validation"],
  "session_id": "sess_abc123"
}
```

### 4.2 Experience Queries
Agents can query past experience:
- `agent_sync experience query "k8s crd"` → Past decisions about K8s CRDs
- `agent_sync experience query "auth" --outcome failure` → What went wrong with auth
- `agent_sync experience query "token" --sort cost` → Most expensive actions

### 4.3 Pattern Library
Over time, experience records form a **pattern library**:
- What libraries work best for each task type
- Which approaches consistently pass review
- Common pitfalls and their workarounds

---

## 5. SDD Protocol — Agent Workflow

### 5.1 Before Session (MANDATORY)

```bash
# 1. Load context for this task type
agent_sync before --task "k8s-phase8"

# 2. Read loaded context
cat agent_memory/sync/context.json   # pre-computed snippets
cat agent_memory/sync/experience.json  # relevant past experiences
cat agent_memory/sync/tokens.json    # current budget status

# 3. Session is now active in agent_memory/sync/session.json
```

**What this loads:**
- Current session ID → all subsequent logs reference it
- Task-relevant context snippets → use these instead of re-reading docs
- Past experience filtered by task patterns → avoid past mistakes
- Remaining token budget → plan work accordingly

### 5.2 During Session (AS YOU GO)

```bash
# Log every meaningful finding immediately
agent_sync log --type finding "Found auth expiry pattern: token refresh missing"
agent_sync log --type decision "Using Go validator for CRD validation"
agent_sync log --type pitfall "watchOS linker fails with duplicate UUIDs"

# Track token-heavy operations
agent_sync token --action "read_doc" --count 3200 --item "docs/STATUS.md"
agent_sync token --action "generate" --count 8500 --item "CRD validator code"
agent_sync token --action "total"  # check running total
```

**When to log:**
- Decision with alternatives considered → log it
- Bug found and fix approach → log it
- Context that was unexpectedly important → log it
- Token-heavy action consumed >5k tokens → log it

### 5.3 After Session (MANDATORY)

```bash
# 1. Close session: compact, summarize, update experience
agent_sync after --summary "Phase 8 CRD validation: built Go validator, all tests pass"

# 2. Verify sync state
agent_sync status
```

**What this does:**
- Compacts verbose logs into concise summaries
- Extracts experience records from findings
- Updates token budget with actual usage
- Archives session for future reference
- Prepares context for next session

---

## 6. Token Accounting

Every session tracks:

| Metric | Tool | Purpose |
|--------|------|---------|
| Prompt tokens | `agent_sync token --action prompt` | Context loading cost |
| Generation tokens | `agent_sync token --action generate` | Code/doc generation cost |
| Read tokens | `agent_sync token --action read` | File reading cost |
| Search tokens | `agent_sync token --action search` | Grep/glob search cost |
| Total | `agent_sync token` | Running session total |

**Progressive compaction triggers:**
- At 60% budget: Warn in status output
- At 80% budget: Auto-compact old logs
- At 95% budget: Emergency prune (archive all but essential context)
- At 100% budget: Session auto-closes, new session required

---

## 7. File Layout

```
agent_memory/sync/
├── MANIFEST.md              # What's here and how it works
├── tokens.json              # Token budget tracker (persistent)
└── .memsearch/              # Zilliz MemSearch semantic storage
    └── memory/              # Markdown-first persistent logs
        ├── sess_abc123.md
        └── sess_def456.md
```

```
scripts/agent_sync.py        # The sync tool (powered by MemSearch API)
```

```
skills/sync-driven-dev.md    # Skill file for agent loading
```

---

## 8. Guardrails

| Rule | Description | Enforcement |
|------|-------------|-------------|
| **Sync-first** | Must run `agent_sync before` before any work | `session.json` must exist |
| **Token honesty** | Report actual token usage, not estimates | Spot-checked by owner |
| **Experience accuracy** | Record actual outcomes, not aspirations | Cross-ref with git log |
| **No ghost sessions** | Every session has a logged after | `after` error if no `before` |
| **Compact discipline** | Don't skip compaction to save time | `after` auto-compacts |

---

## 9. Comparison: SDD vs. Stateless Agent

| Aspect | Stateless Agent | SDD Agent |
|--------|-----------------|-----------|
| Session start | Reads all docs again | Loads compacted context |
| Token cost (avg session) | 40-80k tokens | 15-30k tokens |
| Context freshness | Reads whatever is current | Reads last sync state |
| Experience | None | Structured + queryable |
| Mistake repetition | High | Low (experience query catches it) |
| Compounding | Zero | Positive (each session enriches) |
| Audit trail | None | Full session history |
| Onboarding new agents | Must re-learn everything | Inherits all experience |

---

## 10. Future: Auto-Sync Agents

Long-term vision: The sync layer enables agents that:

1. **Auto-sync from MCP**: A persistent MCP server (`sync-mcp`) that agents connect to via JSON-RPC
2. **Cross-session planning**: Agent can continue work across multiple sessions by reading session history
3. **Multi-agent sync**: Two agents working on different tracks can share context via sync
4. **Failure forensics**: When a session fails, the full sync trail enables root cause analysis
5. **Token ROI analytics**: Measure tokens spent vs. value delivered per phase/track

---

*See [agent_memory/sync/MANIFEST.md](../../agent_memory/sync/MANIFEST.md) for the sync runtime files.*
*See [skills/sync-driven-dev.md](../../skills/sync-driven-dev.md) for the agent skill file.*
*See [scripts/agent_sync.py](../../scripts/agent_sync.py) for the CLI tool.*
