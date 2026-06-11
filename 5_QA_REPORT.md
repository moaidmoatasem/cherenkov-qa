# Cherenkov Dashboard — 5 QA Practitioners Consolidated Report

**Date of Audit:** 2026-06-11
**Target:** Cherenkov Dashboard (`http://localhost:8000`)
**Environment:** Local `uvicorn` instance (`--demo` mode)

## Executive Summary
Five QA personas evaluated the Cherenkov QA Dashboard using static analysis, HTTP profiling, and accessibility heuristics. The dashboard exhibits excellent accessibility and lightweight asset delivery, but suffers from significant backend latency (TTFB) and missing security headers. Testability is moderate, relying on stable `#id` tags rather than standard data attributes.

---

## 1. Accessibility QA
**Score:** 98/100 (via Lighthouse Audit heuristics)
**Status:** **PASS (with minor warning)**

- **Strengths:** ARIA roles, color contrast, and interactive elements are correctly labeled and compliant with WCAG guidelines.
- **Findings:** Only one semantic violation was identified: `heading-order`. An `<h3>` element ("No workspace projects found") within the `projects-screen` skips the `<h2>` level.
- **Action Item:** Ensure the `<h3>` is preceded by an `<h2>`, or promote it to `<h2>` to maintain logical screen reader navigation.

## 2. Performance QA
**Status:** **NEEDS IMPROVEMENT**

- **Strengths:** The frontend payload is exceptionally lightweight. The initial document is just 443 bytes. The JS bundle (~459 KB) and CSS (~78 KB) are delivered rapidly (under 50ms).
- **Findings:** A severe bottleneck was identified on the backend: the Time to First Byte (TTFB) for the base `/` HTML document takes approximately **4.70 seconds**. 
- **Action Item:** Profile the Uvicorn/FastAPI backend to identify blocking I/O operations, slow initializations, or routing delays occurring during the initial page load.

## 3. Security QA
**Status:** **FAIL**

- **Strengths:** No explicit API key exposures or unsafe eval scripts were detected in the base payload.
- **Findings:** The server omits multiple critical HTTP security headers, leaving the frontend vulnerable to fundamental web exploits:
  - Missing `Content-Security-Policy` (CSP) -> Vulnerable to XSS.
  - Missing `X-Frame-Options` -> Vulnerable to Clickjacking.
  - Missing `X-Content-Type-Options` -> Vulnerable to MIME-sniffing.
- **Action Item:** Implement a backend middleware to inject strict security headers (e.g., `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).

## 4. Automation & Testability QA
**Status:** **PASS (with reservations)**

- **Strengths:** The DOM structure heavily utilizes deterministic `id` attributes (e.g., `#overview-screen`, `#workspace-search-input`, `#btn-pilot-run`), making it viable for tool-based testing.
- **Findings:** The codebase completely lacks standard `data-testid` or `data-test-id` attributes. Relying on `#id` and Tailwind CSS utility classes introduces brittleness, as styling changes might inadvertently break Playwright/Selenium test selectors.
- **Action Item:** Refactor the React components to introduce standard `data-testid="..."` attributes for all interactive elements to decouple automated tests from styling/DOM structure.

## 5. Usability QA
**Status:** **NEEDS IMPROVEMENT**

- **Strengths:** Modern SPA architecture allows for seamless client-side transitions once loaded.
- **Findings:** The application fails gracefully. It lacks a `<noscript>` tag warning users if JavaScript is disabled or fails to load. Additionally, a valid favicon is missing (`<link rel="icon" href="data:,">`), which degrades the tab identification experience for users juggling multiple tools.
- **Action Item:** Add a `<noscript>` fallback in the `index.html` and provide a proper favicon.

---
*Report generated autonomously via CHERENKOV Teamwork Orchestration.*
