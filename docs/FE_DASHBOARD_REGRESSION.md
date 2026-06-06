# Cherenkov QA FE Dashboard Full Regression Test Suite

This document contains a comprehensive set of regression test cases for the Cherenkov QA Frontend Dashboard.

## Table of Contents
1. [General Application & Navigation](#general-application--navigation)
2. [Sidebar & TopBar Controls](#sidebar--topbar-controls)
3. [Command Palette](#command-palette)
4. [Projects Screen](#projects-screen)
5. [Setup Screen](#setup-screen)
6. [Pipeline Screen](#pipeline-screen)
7. [Review Screen](#review-screen)
8. [Healing Screen](#healing-screen)
9. [Eject Screen](#eject-screen)
10. [Settings Screen](#settings-screen)
11. [Overview & Truth Map](#overview--truth-map)
12. [Divergences & Signals](#divergences--signals)
13. [Author & Governance](#author--governance)
14. [Memory & UI Kit](#memory--ui-kit)
15. [End-to-End (E2E) Business Flows](#end-to-end-e2e-business-flows)

---

## General Application & Navigation
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| GEN-01 | Initial Load | Open the application URL. | App loads without errors. Mesh background is visible. Sidebar and TopBar render correctly. Default tab is "Projects". |
| GEN-02 | Navigation Stability | Rapidly click through multiple tabs in the sidebar. | No crashes or freezing. The main viewport immediately updates to show the selected screen. |
| GEN-03 | Layout Responsiveness | Resize window from desktop to smaller width. | The application uses flexible layout classes. Content avoids overlapping and overflows gracefully. |

## Sidebar & TopBar Controls
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| NAV-01 | Sidebar Active State | Click on "Setup", then "Review". | The Sidebar highlights the actively selected tab. |
| NAV-02 | TopBar Project Selection | Select a project from the TopBar dropdown (if available) or via Projects tab. | TopBar displays the active project name. |
| NAV-03 | TopBar Autonomy Toggle | In the TopBar, switch autonomy between "Assisted", "Augmented", and "Agentic". | The setting persists. LocalStorage `[copilot] autonomy` updates to reflect the selection. |
| NAV-04 | TopBar Cost & Token Sims | Check the cost and token usage displays. | Values should update to reflect the `totalSpentEstimated` and `tokenUsagePercent` variables. |
| NAV-05 | TopBar Live Drawer | Click the "Live" button on the TopBar. | The Live Execution Drawer opens, hosting the Pipeline Screen. |

## Command Palette
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| CMD-01 | Open Command Palette | Press standard keyboard shortcut (e.g. Cmd/Ctrl + K). | Command palette modal opens and captures focus. |
| CMD-02 | Navigate via Palette | Type "Healing" and press Enter. | Modal closes and active tab switches to Healing screen. |
| CMD-03 | Select Project via Palette | Search for a specific project and select it. | The selected project becomes active, TopBar updates. |
| CMD-04 | Trigger New Run via Palette | Select "New Run" from the command palette. | Setup screen is opened, status resets to "Idle". |

## Projects Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| PRJ-01 | View Projects List | Navigate to "Projects". | A list/grid of initialized projects is shown with metadata. |
| PRJ-02 | Select Project | Click on a project card. | `selectedProjectId` is updated. Simulated token/cost metrics update based on project history. |
| PRJ-03 | Launch New Run | Click "New Run" from the project view. | User is navigated to the Setup Screen. |

## Setup Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| SET-01 | Input Valid Spec | Enter a valid OpenAPI spec path and target URL. Submit. | Validates input and triggers pipeline. Navigates to Pipeline screen. |
| SET-02 | Missing Required Fields | Leave spec path blank and submit. | Form validation errors appear. Pipeline does not start. |

## Pipeline Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| PIP-01 | Monitor Live Execution | Wait on Pipeline screen while `status` is "Live". | Displays streaming character typing simulation. Token usage and cost metrics update proportionally. |
| PIP-02 | Complete Execution | Wait for pipeline to finish. | Automatically navigates to Review Screen and status resets to "Idle". |
| PIP-03 | Drawer Pipeline | Open Pipeline screen from the Live Drawer. | Similar functionality to main pipeline, completes and closes drawer. |

## Review Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| REV-01 | Approve Tests | Approve multiple tests from the review queue. | `handleUpdatePassRateAndCount` triggers, pass rate and counts update for the active project. |
| REV-02 | Reject Tests | Reject generated tests. | They are removed from the queue without increasing pass count. |

## Healing Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| HEA-01 | View Suggestions | Navigate to Healing screen. | List of divergent test suggestions is displayed. |
| HEA-02 | Resolve Suggestion | Accept/Reject a healing suggestion. | `handleSuggestResolveCount` decrements the project's healing count. |

## Eject Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| EJE-01 | Eject Tests | Navigate to Eject screen and initiate code eject. | Displays standard eject interface. Validates that tests run standalone without Cherenkov lock-in. |

## Settings Screen
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| STG-01 | Update Configurations | Change arbitrary settings. | Updates are stored appropriately (local state / local storage) and reflected in UI. |

## Overview & Truth Map
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| OVR-01 | Overview Render | Click Overview. | High-level metrics and system status rendered. |
| TRU-01 | Truth Map Navigation | Open Truth Map. | Renders embedding or conceptual map, ensuring no visual glitches. |

## Divergences & Signals
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| DIV-01 | View Divergences | Navigate to Divergences. | Divergence engine results and state drifts shown. |
| SIG-01 | Review Signals | Navigate to Signals. | Shows analytics, anomaly signals, and trace graphs. |

## Author & Governance
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| AUT-01 | Author Copilot | Open Author tab. | Test authoring components render successfully. |
| GOV-01 | Governance Controls | Open Governance tab. | Enterprise or RBAC governance mockups render. |

## Memory & UI Kit
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| MEM-01 | Memory Visualizer | Open Memory screen. | Vector DB or context memory components appear. |
| UIK-01 | UI Kit Sandbox | Open UI Kit. | Displays all baseline design components (buttons, toasts, inputs) for visual regression. |

## End-to-End (E2E) Business Flows
| Test ID | Title | Steps | Expected Result |
|---|---|---|---|
| E2E-01 | Complete Run Lifecycle | 1. Open App. 2. Select Project. 3. Configure Setup. 4. Wait for Pipeline to finish. 5. Approve generated tests in Review. 6. Eject tests. | User correctly transitions through `Projects -> Setup -> Pipeline -> Review -> Eject`. Token usage and test stats are properly mutated and preserved for the project. |
| E2E-02 | Healing Lifecycle | 1. Trigger run with known anomalies. 2. Navigate to Divergences. 3. Navigate to Healing. 4. Resolve suggestions. | Counts update correctly. The loop finishes with zero unresolved healing suggestions. |
| E2E-03 | Drawer Multi-Tasking | 1. Start a pipeline from Setup. 2. Navigate back to Projects. 3. Open Live Drawer to check status. | Pipeline execution state remains consistent even when navigating away from the main Pipeline tab. |

---
**Note:** As per `AGENTS.md`, Track B/C and Horizon 2 code (dashboard, visual, perf, divergence, governance, etc.) is currently built and unit-tested but **NOT validated**. These frontend regression cases represent testing scenarios that would be applied once the Track A gate passes with real validation evidence.
