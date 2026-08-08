# Session 5: HITL Review & Dashboard

> **Duration:** 5-7 minutes
> **Audience:** QA Managers
> **API:** Demo mode (no live server needed)
> **Key Message:** Human-in-the-loop governance — when the AI isn't sure, it asks a human
> **Difficulty:** Beginner

---

## Hook (5 seconds)

**Voiceover:**
> "What happens when CHERENKOV isn't confident about a test? It doesn't guess. It asks a human. Let me show you the review queue."

*Visual: Terminal with HITL output.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# No server needed — use demo mode
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: The Problem (60 seconds)

### Step 1.1: Explain HITL

**Voiceover:**
> "When CHERENKOV generates a test, it assigns a confidence score. If the score falls in a gray zone — between 0.7 and 0.9 — it flags the test for human review instead of auto-approving or auto-rejecting. This is the Human-in-the-Loop queue."

*Visual: Show a simple diagram or overlay:*

```
Confidence Score:
  < 0.7  → AUTO-REJECT (too uncertain)
  0.7-0.9 → HITL REVIEW (human decides)
  > 0.9  → AUTO-APPROVE (high confidence)
```

**Voiceover:**
> "This prevents two failure modes: accepting bad tests, and rejecting good ones. A human makes the final call."

*[PAUSE — 1 second]*

---

## Part 2: The CLI Workflow (2 minutes)

### Step 2.1: Run Validation (Demo Mode)

**Voiceover:**
> "Let me run a validation that triggers the HITL queue."

**Command:**
```bash
cherenkov validate --target http://localhost:8000 --spec stub/target_spec.json
```

*Expected (one test triggers HITL):*
```
Scenario: happy_path [PASSED]
Scenario: create_user_missing_email [HITL REVIEW REQUIRED]
--------------------------------------------------------------------------------
  Review Triggered:
    Quality Score: 0.78 (HITL Threshold: 0.70 - 0.90)
    Failed Gate:   gate_3_ast (Confidence Check)
    Endpoint:      POST /users
    Item enqueued: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
```

**Voiceover:**
> "See that? `create_user_missing_email` scored 0.78. It's in the gray zone. CHERENKOV won't auto-approve or auto-reject — it's asking a human."

*[PAUSE — 2 seconds]*

### Step 2.2: List the Queue

**Voiceover:**
> "Let's see what's in the review queue."

**Command:**
```bash
cherenkov hitl list
```

*Expected:*
```
HITL queue — pending (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_1bc8ef7a-39c1-4b10-a9fa-80e98f...  pending     conf=0.78  gate=gate_3_ast  POST /users
```

**Voiceover:**
> "One pending item. Score 0.78, failed at the AST confidence gate, on POST /users."

### Step 2.3: Inspect the Item

**Command:**
```bash
cherenkov hitl show ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
```

*Expected:*
```
HITL item: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
  status:             pending
  method/endpoint:    POST /users
  confidence:         0.78
  failed gate:        gate_3_ast
  run ID:             run_20260604T120000Z
  created at:         2026-06-04T12:00:05Z
```

**Voiceover:**
> "Full context. You can see exactly what failed, why, and when. Now the human decides."

*[PAUSE — 1 second]*

### Step 2.4: Approve the Item

**Command:**
```bash
cherenkov hitl approve ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a --actor @alice
```

*Expected:*
```
{
  "ok": true,
  "payload": {
    "id": "ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a",
    "action": "approve",
    "previous_status": "pending",
    "current_status": "approved",
    "actor": "@alice",
    "actor_at": "2026-06-04T12:01:10Z"
  }
}
```

**Voiceover:**
> "Approved by @alice. The item moves to approved status. Full audit trail."

### Step 2.5: Verify Queue is Empty

**Command:**
```bash
cherenkov hitl list --all
```

*Expected:*
```
HITL queue — all (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_1bc8ef7a-39c1-4b10-a9fa-80e98f...  approved    conf=0.78  actor=@alice  POST /users
```

**Voiceover:**
> "Queue cleared. Full audit trail preserved. Who approved it, when, and why."

*[PAUSE — 2 seconds]*

---

## Part 3: The Web Dashboard (2 minutes)

### Step 3.1: Launch Dashboard

**Voiceover:**
> "CLI is great for developers. But QA managers need a visual interface. Let me show the review dashboard."

**Command:**
```bash
cherenkov dashboard
```

*Expected:*
```
CHERENKOV HORIZON V REVIEW SERVER
Starting Review UI Server in DEMO mode...
Loaded 5 mock HITL findings for demonstration.
Server is running on http://localhost:8000
Open this URL in your browser to triage pending items.
```

### Step 3.2: Walk Through the Dashboard

*Visual: Open browser to http://localhost:8000*

**Voiceover:**
> "Here's the dashboard. Let me walk you through what you're seeing."

*Point to each section:*

**Left sidebar:**
> "Navigation. You have conformance maps, the HITL queue, drift findings, and governance KPIs."

**Main panel (HITL Queue):**
> "The review queue. Each item shows the endpoint, confidence score, failed gate, and status. You can approve, reject, or reclassify directly from here."

**Conformance Map:**
> "The spec coverage map. Green means fully covered and passing. Yellow means there are suggestions. Red means drift detected."

**Drift Findings:**
> "Spec drift over time. You can see exactly when an endpoint started violating the contract."

**Governance Panel:**
> "High-level metrics. Total tests, pass rate, drift count, HITL resolution time. This is what your VP of Engineering wants to see."

*[PAUSE — 3 seconds to let the dashboard sink in]*

---

## Closing CTA (5 seconds)

**Voiceover:**
> "Human-in-the-loop governance. CLI for developers, dashboard for managers. Full audit trail. That's CHERENKOV."

*Visual: Dashboard screenshot or project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 7 minutes
- [ ] HITL queue is clearly explained
- [ ] The dashboard loads and is navigable
- [ ] Each dashboard section is pointed out
- [ ] The approve workflow is complete (list → show → approve → verify)
- [ ] Voiceover explains *why* HITL matters (prevents false positives/negatives)

---

## Editing Notes

- **Overlay** the confidence score diagram during Step 1.1
- **Zoom** on the HITL queue item during Step 2.2
- **Split screen** during Part 3: terminal left, browser right
- **Add** cursor highlights on each dashboard section as it's explained
- **Speed up** the dashboard load time if > 3 seconds
