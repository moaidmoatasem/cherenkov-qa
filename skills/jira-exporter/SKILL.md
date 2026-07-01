---
name: jira-exporter
description: "Suggest-only Jira export for failed validation items via the MCP export_jira_ticket tool."
scope: Track C Re-integration
invariants: [D7]
---

# Jira Exporter Skill

## Purpose
Suggest-only Jira export for failed validation items (D7 invariant).

## Tools
Exposed to MCP via `export_jira_ticket`.

## Usage for Agents
Invoke `export_jira_ticket` through MCP with an `item_id`. It will format a bug report but will not auto-submit without user approval.
