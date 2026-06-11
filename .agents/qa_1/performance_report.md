# Cherenkov Dashboard Performance QA Report

## Overview
A performance evaluation of the Cherenkov dashboard running at `http://localhost:8000` was requested.

## Methodology & Findings
1. **Tooling Access**: The requested `chrome-devtools-mcp` tools (`call_mcp_tool`) were not mapped or exposed in the current subagent's tool context, preventing direct lazy tool invocation of `lighthouse_audit` and `performance_start_trace` through the MCP API.
2. **Lighthouse CLI**: Fallback execution via `npx lighthouse http://localhost:8000 --headless` generated the initial audit data but failed on Windows with an `EPERM` permission error when attempting to tear down its temporary Chrome profile directory (`C:\Users\moaid\AppData\Local\Temp\lighthouse.*`), which prevented the final `lighthouse.json` artifact from being successfully saved.
3. **Direct Measurement**: A fallback Node.js performance fetch against `http://localhost:8000` was performed to gather baseline statistics.

## Baseline Metrics
- **Initial Document Load Time**: ~490.17 ms
- **Document Size**: 443 bytes

## Conclusion
The dashboard's baseline initial HTML response is quite fast (490ms) and lightweight (443 bytes). However, to generate a comprehensive Lighthouse or Core Web Vitals report, the MCP server tools (`call_mcp_tool`) must be exposed to the evaluating agent, or the system permissions on Windows temp directories need to be resolved to allow the Lighthouse CLI to successfully tear down and output its json report.
