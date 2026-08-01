# Handoff Report — Phase M0 - E0.5d: Spec-Shape Conformance Corpus Review

**Agent ID**: reviewer_1  
**Timestamp**: 2026-08-01T17:52:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### Observation 1.1: Missing `specs/corpus/` Directory & Local OpenAPI Specifications
- **Command**: `list_dir` on `Z:\home\moaid\cherenkov-qa\specs\corpus`
- **Result**: `Encountered error in step execution: directory Z:\home\moaid\cherenkov-qa\specs\corpus does not exist`
- **Context**: The mission required `specs/corpus/` to contain ≥10 valid, stored OpenAPI 3.x specifications (Stripe, GitHub, Twilio, Kubernetes, OpenAI, Petstore, Slack, Box, SendGrid, DigitalOcean). No specs were stored in `specs/corpus/`. Instead, `demos/conformance_corpus/evaluate_corpus.py` (lines 11-22) fetched specs dynamically over HTTP, missing Box and SendGrid entirely (substituting Discord and GitLab), and 3 of the 10 URLs failed to load at runtime.

### Observation 1.2: Missing `scripts/run_conformance_corpus.py`
- **Command**: `find_by_name` for `*run_conformance_corpus*` in `Z:\home\moaid\cherenkov-qa`
- **Result**: `Found 0 results`
- **Context**: The required production script `scripts/run_conformance_corpus.py` was not created. Instead, a demo script `demos/conformance_corpus/evaluate_corpus.py` was created, which bypassed the `cherenkov verify` CLI engine and imported internal functions directly (`_load_spec`, `unprobed_endpoints`, `plan_probes`).

### Observation 1.3: Invariant Violation — `Total Endpoints != Probes Planned + Dropped Endpoints` on Kubernetes Spec
- **File**: `corpus_report.md` (lines 312-325) & `demos/conformance_corpus/evaluate_corpus.py` (lines 40-46)
- **Verbatim Data from `corpus_report.md`**:
  ```markdown
  ### Kubernetes
  - Total Operations: 1190
  - Probes Planned: 249
  - Endpoints Dropped: 947
  ```
- **Math**: `249 (Probes Planned) + 947 (Endpoints Dropped) = 1196`
- **Mismatch**: `1196 != 1190` (`Total Operations` is 1190, undercounting by 6).
- **Code Bug in `evaluate_corpus.py`**:
  ```python
  44: for m in path_item.keys():
  45:     if m.lower() in ("get", "post", "put", "delete", "patch"):
  46:         total_ops += 1
  ```
  Line 45 omitted `HEAD` operations from `total_ops`, while `unprobed_endpoints` counted 6 `HEAD` operations under drop reason `no probe for HEAD: a happy-path probe is GET-only...` (line 35 of `corpus_report.md`), causing the accounting equation `Total Endpoints = Probes Planned + Dropped Endpoints` to fail.

### Observation 1.4: 3 Specs Failed to Load in Benchmark Run
- **File**: `corpus_report.md` (lines 173, 299, 301)
- **Verbatim Data**:
  - Line 173: `### Slack` -> `**Error loading/parsing:** Failed to load`
  - Line 299: `### GitLab` -> `**Error loading/parsing:** Failed to load`
  - Line 301: `### Petstore` -> `**Error loading/parsing:** Failed to load`
- **Context**: 3 out of the 10 specs in the benchmark script failed to load/parse due to unhandled network issues or OpenAPI 2.0/3.0 schema incompatibilities, resulting in zero verification coverage for 30% of the corpus.

### Observation 1.5: Missing `docs/marketing/E0.5d_conformance_corpus.md`
- **Command**: `list_dir` on `Z:\home\moaid\cherenkov-qa\docs\marketing`
- **Result**: Contains only `CATCH_THE_AI_CHEATING_WRITEUP.md` and `product_hunt_kit.md`. `E0.5d_conformance_corpus.md` is missing.
- **Context**: The mission required a polished marketing write-up at `docs/marketing/E0.5d_conformance_corpus.md` containing drop reason taxonomy, metric tables, readability formatting, and Phase M1 practitioner recruitment call-to-action. Instead, a raw markdown dump was generated at root `corpus_report.md`.

### Observation 1.6: Test Suite Execution Output
- **Command**: `wsl bash -c "cd /home/moaid/cherenkov-qa && .venv/bin/pytest"`
- **Result**: `........sss........................ [100%]` (29 passed, 3 skipped, 0 failed).

---

## 2. Logic Chain

1. **Premise**: Delivering Phase M0 - E0.5d requires: (a) `specs/corpus/` containing local OpenAPI specs for 10 specific services, (b) `scripts/run_conformance_corpus.py` executing `cherenkov verify`, (c) strict adherence to the ZERO SILENT DROP invariant `Total Endpoints = Probes Planned + Dropped Endpoints` across all specs, (d) `docs/marketing/E0.5d_conformance_corpus.md` with marketing write-up & CTA, and (e) passing test suite.
2. **Step 1**: Observation 1.1 proves `specs/corpus/` does not exist and no spec files were stored locally. Storing specs locally is necessary to guarantee repeatable, offline, version-controlled testing without network dependence.
3. **Step 2**: Observation 1.2 proves `scripts/run_conformance_corpus.py` was omitted and replaced by an internal function demo `demos/conformance_corpus/evaluate_corpus.py`.
4. **Step 3**: Observation 1.3 proves that the ZERO SILENT DROP accounting invariant failed on Kubernetes (`1190 != 249 + 947`) due to a bug in `evaluate_corpus.py` filtering out `HEAD` methods during total counting while including them in drop counting.
5. **Step 4**: Observation 1.4 proves that 3 out of 10 corpus specs failed to load at all (Slack, GitLab, Petstore), violating the requirement of 10 valid OpenAPI specs.
6. **Step 5**: Observation 1.5 proves that `docs/marketing/E0.5d_conformance_corpus.md` was omitted, lacking the required practitioner recruitment call-to-action and marketing taxonomy.
7. **Conclusion**: The deliverable fails requirements 1, 2, 3, and 4, and exhibits shortcuts and accounting violations. Per reviewer and critic guidelines, the verdict MUST be `REQUEST_CHANGES` with a Critical finding tagged as `INTEGRITY VIOLATION`.

---

## 3. Caveats

- Unit tests in `tests/` pass (29 passed, 3 skipped).
- The underlying `cherenkov.divergence.probe_planner` module logic itself correctly categorizes dropped endpoints; the accounting mismatch in Observation 1.3 was caused by the evaluation runner script omitting `HEAD` from `total_ops` rather than a bug in `probe_planner.py`.
- Network availability may have contributed to raw GitHub URLs failing to load during script execution, further underscoring the necessity of storing specs locally in `specs/corpus/`.

---

## 4. Conclusion & Review Verdict

**Verdict**: **REQUEST_CHANGES**

### Findings

#### [Critical] Finding 1 — INTEGRITY VIOLATION / MISSING ARTIFACTS: Omission of `specs/corpus/`, `scripts/run_conformance_corpus.py`, and `docs/marketing/E0.5d_conformance_corpus.md`
- **What**: The core deliverables of Phase E0.5d were bypassed or placed in incorrect non-conforming locations.
- **Where**: `specs/corpus/` (missing), `scripts/run_conformance_corpus.py` (missing), `docs/marketing/E0.5d_conformance_corpus.md` (missing).
- **Why**: 
  1. Relying on external network URLs instead of storing specs in `specs/corpus/` caused 30% of specs (Slack, GitLab, Petstore) to fail loading. Furthermore, Box and SendGrid were completely missing.
  2. Bypassing `cherenkov verify` CLI engine in favor of internal function calls in `demos/conformance_corpus/evaluate_corpus.py` prevents E2E verification of CLI capability.
  3. Omitting `docs/marketing/E0.5d_conformance_corpus.md` misses the Phase M1 practitioner recruitment call-to-action and marketing documentation goals.
- **Suggestion**: 
  1. Download and commit valid OpenAPI 3.x specs for Stripe, GitHub, Twilio, Kubernetes, OpenAI, Petstore, Slack, Box, SendGrid, DigitalOcean into `specs/corpus/`.
  2. Implement `scripts/run_conformance_corpus.py` that invokes the `cherenkov verify` engine on all files in `specs/corpus/`.
  3. Create `docs/marketing/E0.5d_conformance_corpus.md` with complete metrics, drop reason taxonomy, and Phase M1 recruitment CTA.

#### [Critical] Finding 2 — INVARIANT VIOLATION: Accounting mismatch on Kubernetes spec (`Total Endpoints != Probes Planned + Dropped Endpoints`)
- **What**: The ZERO SILENT DROP invariant `Total Endpoints = Probes Planned + Dropped Endpoints` was violated on Kubernetes (`1190 != 249 + 947`, off by 6).
- **Where**: `demos/conformance_corpus/evaluate_corpus.py:45` & `corpus_report.md` line 312.
- **Why**: Line 45 of `evaluate_corpus.py` checked `if m.lower() in ("get", "post", "put", "delete", "patch"):`, omitting `head` and other HTTP methods from `total_ops`. However, `unprobed_endpoints` included `head` operations (6 dropped HEAD ops), causing total operations to be recorded as 1190 instead of 1196.
- **Suggestion**: Include `"head"` (and all valid OpenAPI HTTP methods: `get`, `post`, `put`, `delete`, `patch`, `head`, `options`, `trace`) when calculating total operations, and add an automated assertion asserting `total_ops == planned_probes + unprobed_count`.

#### [Major] Finding 3 — Unhandled Schema / Loading Errors for Slack, GitLab, Petstore
- **What**: 3 specs in the evaluation failed to load completely.
- **Where**: `demos/conformance_corpus/evaluate_corpus.py:33` (`_load_spec`).
- **Why**: Specs fetched over HTTP returned errors or contained OpenAPI 2.0 (Swagger) constructs that `_load_spec` failed to handle gracefully.
- **Suggestion**: Ensure pre-validated OpenAPI 3.x files are stored locally in `specs/corpus/` and convert any OpenAPI 2.0 specs to 3.0 or validate them prior to inclusion in the corpus.

---

## 5. Verified Claims & Unverified Items

### Verified Claims
| Claim | Method | Result |
|---|---|---|
| Unit tests pass | Executed `wsl bash -c "cd /home/moaid/cherenkov-qa && .venv/bin/pytest"` | PASS (29 passed, 3 skipped) |
| Invariant holds on Stripe, GitHub, OpenAI, Discord, DigitalOcean, Twilio | Verified sum of probes + dropped in `corpus_report.md` | PASS |
| Invariant holds on Kubernetes | Checked `corpus_report.md` math: 1190 vs 249+947=1196 | **FAIL (Invariant Violation)** |
| `specs/corpus/` contains 10 local OpenAPI specs | `list_dir` on `Z:\home\moaid\cherenkov-qa\specs\corpus` | **FAIL (Directory missing)** |
| `scripts/run_conformance_corpus.py` exists | `find_by_name` on repo | **FAIL (File missing)** |
| `docs/marketing/E0.5d_conformance_corpus.md` exists | `list_dir` on `docs/marketing` | **FAIL (File missing)** |

---

## 6. Verification Method for Remediation

To verify the fixes after remediation:
1. Confirm directory exists and has 10 specs:
   `ls specs/corpus/*.json specs/corpus/*.yaml`
2. Run conformance script:
   `python scripts/run_conformance_corpus.py`
3. Verify zero silent drop invariant across all 10 specs:
   `python -c "import json; data=json.load(open('corpus_results.json')); assert all(d['total'] == d['planned'] + d['dropped'] for d in data.values())"`
4. Verify marketing document exists and contains CTA:
   `cat docs/marketing/E0.5d_conformance_corpus.md`
5. Run full test suite:
   `pytest`
