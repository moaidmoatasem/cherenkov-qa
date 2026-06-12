# UX Revamp Summary — For Product & Architecture Review

## Core Problem Statement
The current dashboard delivers features but lacks a **cohesive QA-first user experience**. Manual testers (Maya, persona) get a generic "generate tests" flow, not a guided journey. QA leads see lists without risk prioritization. SDETs don't see pattern learning. The **QA Reasoning Engine** (ADR-007) provides the backend intelligence; the FE needs transformation to expose it.

---

## UX Transformation Vision

### Before → After
| Aspect | Before | After |
|--------|--------|-------|
| **Landing** | Projects list | Release readiness KPI + top divergences + recent learning |
| **Navigation** | Flat list of 15+ items | Grouped IA (OVERVIEW/ENGINE/AUTHOR/SIGNALS/OPERATE/LEARN) |
| **Manual QA** | Type intent → "Pilot run" mock | Type intent → live step preview → vision fallback → eject |
| **Divergences** | List with class/severity/status | Risk-scored + confidence-weighted + quick actions |
| **Learning** | Memory screen exists but isolated | Idioms surface during authoring/triage, compounding value visible |

---

## Key Requirements

### 1. Manual QA Journey (Author by Intent)
- **Live step preview** with vision confirmation (not just start/run)
- **Mentor idioms** inline: "Seniors check tenant isolation here"
- **Vision fallback**: "3 candidates, pick one" when element not found
- **Eject confirmation**: Shows file path + "runs standalone" message

### 2. QA Lead Journey (Divergence Triage)
- **Risk score column**: Derived from likelihood × impact (QAPlan.risk_register)
- **Confidence indicator**: "Reproduced 4/5 runs" for flakiness detection
- **Quick actions**: a/r/c keyboard shortcuts, hover-approve without drawer
- **Evidence diff**: Side-by-side claim A vs claim B with lazy loading

### 3. SDET Journey (Pattern Learning)
- **Session counter**: "3 new patterns learned this session"
- **Decay visualization**: Older idioms fade, recent ones prominent
- **Apply action**: Copy idiom into intent field as template

### 4. Integrity Requirements (Solution Architect)
- **D7 invariant**: Never auto-edit test code. FE shows suggestions only.
- **Zero lock-in**: Eject produces vanilla Playwright. FE verifies via smoke test.
- **Spec-derived**: Expected values from spec, not LLM. FE shows provenance chips.
- **Graceful degradation**: OfflineOverlay + mock-first pattern (lib/api.ts).

---

## Implementation Plan

| Week | Focus | Screens | Key BE Contracts |
|------|-------|---------|------------------|
| 1 | Defect fixes + Risk integration | DivergencesScreen, EjectScreen, AuthorScreen | riskScore, confidence on divergence |
| 2 | QA Plan + Mentor | QAPlanScreen (new), AuthorScreen | /api/v1/reasoning/plan, /api/v1/memory/idioms |
| 3 | DevOps enablement | GovernanceScreen, SignalsScreen | /api/v1/governance/k8s, /api/v1/signals |
| 4 | Testing + polish | All screens | a11y audit, regression tests |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Glow-heavy theme fails WCAG AA | text-primary for body text only, glow for accents |
| Too many screens overwhelm | Onboarding tour + progressive disclosure |
| BE not ready | Mock-first contract, build with mocks |
| Risk scoring not mature | Start static, evolve with QAPlan |

---

## Acceptance Criteria

✅ Manual QA can author/eject first test in <10 min  
✅ QA Lead can triage 5 divergences with risk sorting  
✅ SDET sees patterns learned counter increment  
✅ All screens load in mock mode (lib/api.ts pattern)  
✅ WCAG AA contrast verified  
✅ Keyboard shortcuts working (j/k, a/r/c)  
✅ Reduced-motion preference honored  
✅ Zero CHERENKOV imports in ejected tests (smoke test)

---

*Detailed requirements in `docs/FE_QA_WORKFLOW_REQUIREMENTS.md`*