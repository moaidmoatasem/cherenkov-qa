---
scope: Track B Re-integration
invariants: [D7]
---

# Visual Diff Baseline Skill

## Purpose
Run visual screenshot baselines and regression checks against the local UI.

## Tools
Exposed to MCP via `visual_diff_baseline`.

## Usage for Agents
Call `visual_diff_baseline` through MCP. It will run Playwright and verify image matching. Ensure target URL is up before running.
