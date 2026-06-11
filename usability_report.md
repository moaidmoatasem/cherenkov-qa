# Usability & UX Report: Cherenkov Dashboard

**Date:** 2026-06-11
**Target:** `http://localhost:8000`
**Methodology:** Automated Playwright Headless Render + DOM Heuristic Evaluation

## Overview

The Cherenkov Dashboard was evaluated for accessibility and UX/UI issues. A headless Chrome instance captured the rendered DOM and simulated interaction to identify common usability pitfalls.

## Findings

### 1. Honest Offline State ("Checking" Overlay)
- **Observation:** The application immediately displays an overlay: *"Connecting to the Cherenkov engine… Probing the review API on /api/v1/health. CHECKING…"*.
- **UX Impact:** This serves as the "Honest offline state" (Issue #221). While functional, if the backend is genuinely offline, this state may block user interaction indefinitely without offering a clear timeout or bypass to access local cached data or settings.
- **Recommendation:** Introduce a timeout to the `OfflineOverlay` that transitions from "CHECKING…" to a definitive "OFFLINE" state with a clear "Retry" button, rather than leaving the user in an ambiguous loading state.

### 2. Mock Data Banner
- **Observation:** The dashboard explicitly informs the user when it is in a disconnected state: *"This view is currently rendering static mock data for demonstration purposes. It is not connected to a live backend endpoint."*
- **UX Impact:** Excellent for setting user expectations. This prevents confusion regarding data provenance.

### 3. Accessibility (A11y)
- **Observation:** A scan of the rendered DOM for missing `aria-label` or inner text on `<button>`, missing `alt` attributes on `<img>`, and missing `href` on `<a>` tags returned **0 issues**.
- **UX Impact:** The core structural components appear to follow good accessibility practices for interactive elements.
- **Recommendation:** Maintain this standard. Consider adding contrast ratio checks for the "glow-blue" against "bg-base" in future UI Kit iterations.

### 4. Information Architecture & Navigation
- **Observation:** The sidebar contains numerous navigation sections (Overview, Truth Map, Divergences, Explore, Author by Intent, Review Queue, Signals, Healing Options, Devices, Eject Suite, Governance, Memory, Knowledge, Chat, Settings).
- **UX Impact:** While comprehensive, the sheer volume of navigation items (15+) may overwhelm new users.
- **Recommendation:** The "Guided Tour" and "Onboarding Wizard" features (observed in `App.tsx`) are critical here. Ensure they are prominent for first-time users. Consider grouping the sidebar items into collapsible categories (e.g., LEARN, OPERATE) visually to reduce cognitive load. (They appear grouped by headers but could be collapsible).

### 5. Token & Cost Observability
- **Observation:** The UI displays real-time simulated metrics like *"43% USED"* and *"SESSION COST (DEMO): $0.14 | Cloud equivalent: $0.476"*.
- **UX Impact:** Highly visible cost transparency is a strong UX positive for AI-driven tools.
- **Recommendation:** Ensure these metrics have tooltips explaining the "Cloud equivalent" calculation to build trust.

## Conclusion
The dashboard presents a highly sophisticated, data-rich interface. The primary usability risk lies in the offline/loading states and the dense information architecture. The baseline accessibility of semantic HTML elements is strong.
