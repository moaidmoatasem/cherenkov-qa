# CHERENKOV-QA 90-Second Demo Script

**Goal:** Convert skeptics by showing the end-to-end flow from spec to a caught bug, without requiring a SaaS signup.

**Visual Constraints:** 
- Keep the terminal font large.
- No voiceover is strictly needed (use text pop-ups/subtitles), but voiceover is recommended.
- Total time: ~90 seconds.

---

## 0:00 - 0:10 (The Hook & Ingestion)

**Visual:** Terminal open. An OpenAPI YAML file is shown quickly.
**Subtitle:** "Your OpenAPI spec says one thing. Does your server agree?"
**Action:** User types `npx cherenkov init --spec petstore.yaml --target http://localhost:8080`
**Narration/Subtitle:** "CHERENKOV reads your spec and generates typed Playwright tests locally using an LLM. Zero vendor lock-in. Zero cloud data sharing."

## 0:10 - 0:30 (Generation & 6-Gate Review)

**Visual:** Terminal showing progress bars for generation. 
**Action:** The CLI logs:
- `[AST Gate] Passed`
- `[Syntax Gate] Passed`
- `[Prism Mock Gate] Passed`
**Narration/Subtitle:** "Generated tests pass a rigorous 6-gate review. They compile and work against a mock server before they ever touch your real API."

## 0:30 - 0:50 (Execution & Conformance Drift Detection)

**Visual:** CLI executes the tests using Playwright. 
**Action:** Tests run. One test fails with a red `X`.
- `POST /pet - Expected: 422 Unprocessable Entity`
- `Actual: 400 Bad Request`
**Narration/Subtitle:** "We just caught spec drift. The spec demands a 422 for missing fields, but the live server returned a 400. Clients relying on the spec would crash."

## 0:50 - 1:10 (Suggest-Only Healing)

**Visual:** CLI prompts with a healing suggestion. 
**Action:** 
- `Suggestion: Add tighter value assertions for the response body.`
- `Diff:` (shows the suggested code addition)
**Narration/Subtitle:** "CHERENKOV suggests how to tighten the test or fix the spec, but it NEVER auto-edits your code. You stay in control."

## 1:10 - 1:30 (Eject & Call to Action)

**Visual:** User types `cherenkov eject --output ./tests`
**Action:** A clean, vanilla Playwright test file is generated without any proprietary imports.
**Narration/Subtitle:** "Don't want to use CHERENKOV forever? Just eject. You get standard Playwright tests you can run anywhere."

**Visual:** Black screen with logo and URL.
**Subtitle:** "Catch API drift before production. Get started: cherenkov.dev"
