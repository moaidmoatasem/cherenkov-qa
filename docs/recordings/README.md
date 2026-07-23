# CHERENKOV QA — Loom Recording Library

**8 onboarding & demo sessions** with full voiceover scripts, commands, expected output, and visual cues.

> **Format:** Loom / screen recording scripts (adapt for OBS, Camtasia, or any recording tool).
> **Audience:** Developers, QA Engineers/SDETs, Engineering Managers/Leads, DevOps.

---

## Session Index

| # | Title | Duration | Audience | API | File |
|---|-------|----------|----------|-----|------|
| 1 | [60-Second Quickstart](session_01_quickstart.md) | 2-3 min | Developers | Petstore (live) | `session_01_quickstart.md` |
| 2 | [Catch the AI Cheating](session_02_catch_cheating.md) | 5-7 min | Dev + QA | Controllable target | `session_02_catch_cheating.md` |
| 3 | [Spec to Verified Suite](session_03_full_workflow.md) | 7-10 min | QA / SDETs | Controllable target | `session_03_full_workflow.md` |
| 4 | [Live Case: Real API](session_04_live_api.md) | 5-7 min | Dev + QA | JSONPlaceholder (live) | `session_04_live_api.md` |
| 5 | [HITL Review & Dashboard](session_05_hitl_dashboard.md) | 5-7 min | QA Managers | Demo mode | `session_05_hitl_dashboard.md` |
| 6 | [CI/CD Integration](session_06_cicd_integration.md) | 5-7 min | DevOps / Leads | Controllable target | `session_06_cicd_integration.md` |
| 7 | [The Business Case](session_07_business_case.md) | 7-10 min | Eng Managers | Dashboard + metrics | `session_07_business_case.md` |
| 8 | [Zero Lock-in: Eject](session_08_eject_freedom.md) | 3-5 min | Skeptics | Petstore | `session_08_eject_freedom.md` |

---

## Recommended Recording Order

1. **Session 1** — Record first. It's the fastest and proves the tool works.
2. **Session 2** — The hook. Shows the problem CHERENKOV solves.
3. **Session 8** — Addresses the #1 objection upfront (lock-in).
4. **Session 3** — Deep dive for QA engineers who want the full picture.
5. **Session 4** — Proves it works against real APIs, not just localhost.
6. **Session 5** — For managers who need visibility.
7. **Session 6** — For DevOps who need CI integration.
8. **Session 7** — The pitch deck companion for leadership.

---

## Recording Setup

### Terminal Settings
- **Font:** Fira Code or JetBrains Mono, 16-18pt
- **Theme:** Dark (Dracula, One Dark, or similar)
- **Terminal:** iTerm2 (macOS) or Windows Terminal with WSL
- **Window:** 120x40 minimum, maximize for recording

### Loom Settings
- **Camera:** Optional (top-right corner for personal touch)
- **Screen:** Full screen, single monitor preferred
- **Audio:** External mic if available, quiet room
- **Resolution:** 1080p minimum

### Before Each Recording
1. Clear terminal history (`clear` or fresh tab)
2. Close unrelated tabs/windows
3. Disable notifications (Do Not Disturb)
4. Test audio levels
5. Run the prerequisites once to verify they work

---

## Using These Scripts

Each session file contains:

- **Hook** — Opening line (first 5 seconds, most critical)
- **Prerequisites** — Exact setup commands to run BEFORE recording
- **Step-by-step** — Each action with exact command, expected output, and voiceover script
- **Visual cues** — Where to zoom, highlight, or overlay text
- **Pause points** — Natural cuts for editing
- **Closing CTA** — What to say at the end

### Voiceover Conventions
- **Bold text** = Verbatim voiceover (read this exactly)
- `Code blocks` = Commands to type (type these exactly)
- *Italics* = Visual cues / editor instructions
- `Expected:` = What should appear on screen
- `[PAUSE]` = 1-2 second pause for dramatic effect

---

## Live Evidence (Captured 2026-07-06)

All demos were executed against real targets. Raw output saved in [`evidence/SESSION_EVIDENCE.md`](evidence/SESSION_EVIDENCE.md).

| Demo | Result | Key Finding |
|------|--------|-------------|
| Catch the AI Cheating (Python) | PASS | 1/3 cheats caught statically |
| Catch the AI Cheating (TypeScript) | PASS | 2/3 cheats caught by Gate 4 |
| Validate vs Target API | 10/16 passed | `password_too_short`: Expected 422, Got 400 |
| Hallucination detection | CAUGHT | `auth_token` field not in spec |
| Eject | PASS | Clean client.ts, zero CHERENKOV deps |
| HITL queue | 16 pending | Confidence-scored review items |
| HITL approve | PASS | Item approved, queue 16 → 15 |
| Check-suite | CAUGHT | DELETED test detected via AST |
| Spec diff | PASS | 19 breaking + 2 additive changes detected |
| Governance | PASS | KPI panel (health 0.70, escape rate 0.0%) |
| Doctor | All OK | Ollama, Node, Playwright, Docker healthy |

---

## Distribution

After recording, upload to:
1. **Loom** — For internal sharing and embedding in Notion/Confluence
2. **YouTube (unlisted)** — For external sharing with prospects
3. **GitHub README** — Embed Loom links or asciinema casts
4. **Sales deck** — Link to Session 7 for executive pitch
