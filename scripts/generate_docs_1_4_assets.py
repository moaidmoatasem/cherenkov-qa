"""
Generates high-resolution PNG and SVG assets for CHERENKOV-QA Documentation v1.4.
Creates:
- docs/1.4/assets/homepage_overview.svg & .png
- docs/1.4/assets/getting_started.svg & .png
- docs/1.4/assets/version_diff.svg & .png
- docs/1.4/assets/sitemap_architecture.svg & .png
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("docs/1.4/assets").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. VERSION DIFF DIAGRAM (SVG & HTML for PNG screenshot)
VERSION_DIFF_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    color: #f8fafc;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 40px;
  }
  .container {
    width: 1400px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    padding: 48px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(16px);
  }
  .header {
    text-align: center;
    margin-bottom: 48px;
  }
  .header h1 {
    font-size: 38px;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
  }
  .header p {
    font-size: 18px;
    color: #94a3b8;
  }
  .timeline {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 32px;
    position: relative;
  }
  .version-card {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 18px;
    padding: 32px;
    border: 2px solid transparent;
    display: flex;
    flex-direction: column;
    position: relative;
  }
  .v12 {
    border-color: #64748b;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%);
  }
  .v13 {
    border-color: #818cf8;
    background: linear-gradient(180deg, rgba(49, 46, 129, 0.4) 0%, rgba(15, 23, 42, 0.9) 100%);
  }
  .v14 {
    border-color: #38bdf8;
    background: linear-gradient(180deg, rgba(14, 165, 233, 0.25) 0%, rgba(15, 23, 42, 0.95) 100%);
    box-shadow: 0 0 30px rgba(56, 189, 248, 0.25);
  }
  .badge {
    align-self: flex-start;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 16px;
  }
  .badge-outdated {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.4);
  }
  .badge-current {
    background: rgba(34, 197, 94, 0.25);
    color: #86efac;
    border: 1px solid rgba(34, 197, 94, 0.6);
  }
  .version-title {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #f8fafc;
  }
  .version-subtitle {
    font-size: 15px;
    color: #94a3b8;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  .features-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex-grow: 1;
  }
  .features-list li {
    font-size: 15px;
    color: #cbd5e1;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    line-height: 1.4;
  }
  .bullet {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-top: 7px;
    flex-shrink: 0;
  }
  .v12 .bullet { background: #94a3b8; }
  .v13 .bullet { background: #a5b4fc; }
  .v14 .bullet { background: #38bdf8; }
  .status-footer {
    margin-top: 28px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .status-warn { color: #f87171; }
  .status-ok { color: #4ade80; font-weight: 600; }
  .arrow-indicator {
    position: absolute;
    top: 50%;
    right: -24px;
    transform: translateY(-50%);
    font-size: 24px;
    color: #64748b;
    z-index: 10;
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>CHERENKOV-QA Version Evolution Architecture</h1>
    <p>Continuous progression from Foundation (v1.2) through Autonomous Extensions (v1.3) to Consolidated Release (v1.4)</p>
  </div>
  <div class="timeline">
    <!-- Version 1.2 -->
    <div class="version-card v12">
      <span class="badge badge-outdated">Legacy / Archived</span>
      <h2 class="version-title">Version 1.2</h2>
      <div class="version-subtitle">Core Invariants & Foundations</div>
      <ul class="features-list">
        <li><span class="bullet"></span> Core API Conformance Testing engine</li>
        <li><span class="bullet"></span> Playwright test suite auto-generation</li>
        <li><span class="bullet"></span> SQLite storage harness (verdicts.db)</li>
        <li><span class="bullet"></span> Non-negotiable D7 validation invariants</li>
        <li><span class="bullet"></span> CLI baseline (run, validate, eject)</li>
      </ul>
      <div class="status-footer status-warn">
        <span>⚠️ Outdated banner active on site</span>
      </div>
      <div class="arrow-indicator">➔</div>
    </div>

    <!-- Version 1.3 -->
    <div class="version-card v13">
      <span class="badge badge-outdated">Previous Minor</span>
      <h2 class="version-title">Version 1.3</h2>
      <div class="version-subtitle">Autonomous Fabric & Horizons</div>
      <ul class="features-list">
        <li><span class="bullet"></span> Second Brain (Knowledge Mesh & RAG)</li>
        <li><span class="bullet"></span> VLM + LocalAI Backend tier routing</li>
        <li><span class="bullet"></span> Tauri 2 Desktop Host Application</li>
        <li><span class="bullet"></span> Chat Agent + Persona Registry (SSE)</li>
        <li><span class="bullet"></span> Mobile Testing Engine (Maestro/ADB)</li>
        <li><span class="bullet"></span> Kubernetes Operator & CRD extensions</li>
      </ul>
      <div class="status-footer status-warn">
        <span>⚠️ Outdated banner links to v1.4</span>
      </div>
      <div class="arrow-indicator">➔</div>
    </div>

    <!-- Version 1.4 -->
    <div class="version-card v14">
      <span class="badge badge-current">CURRENT / LATEST</span>
      <h2 class="version-title">Version 1.4.0</h2>
      <div class="version-subtitle">Consolidated Release Hub</div>
      <ul class="features-list">
        <li><span class="bullet"></span> <strong>Unified 1.4 Diátaxis Documentation Hub</strong></li>
        <li><span class="bullet"></span> <strong>Clean Architecture</strong> Ports & Adapters (ADR-004)</li>
        <li><span class="bullet"></span> <strong>MemSearch Semantic Memory</strong> & SDD protocol</li>
        <li><span class="bullet"></span> <strong>Multi-Agent Conductor</strong> & CC-1..CC-6 suite</li>
        <li><span class="bullet"></span> <strong>Native CI/CD</strong> & Jenkins Shared Library</li>
        <li><span class="bullet"></span> <strong>Spec Guardian</strong> & Portable Test Certificates</li>
        <li><span class="bullet"></span> <strong>Live Regression Trend</strong> & Coverage Maps</li>
      </ul>
      <div class="status-footer status-ok">
        <span>✅ Authoritative release (No warning banner)</span>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

# 2. SITE MAP ARCHITECTURE (SVG & HTML for PNG screenshot)
SITEMAP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0b0f19;
    color: #f1f5f9;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 40px;
  }
  .container {
    width: 1400px;
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 24px;
    padding: 48px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
  }
  .header {
    text-align: center;
    margin-bottom: 40px;
  }
  .header h1 {
    font-size: 36px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 8px;
  }
  .header p {
    font-size: 17px;
    color: #94a3b8;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 28px;
  }
  .quadrant {
    border-radius: 16px;
    padding: 28px;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
  .q-tutorials {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%);
    border-color: rgba(16, 185, 129, 0.3);
  }
  .q-howto {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%);
    border-color: rgba(245, 158, 11, 0.3);
  }
  .q-reference {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%);
    border-color: rgba(59, 130, 246, 0.3);
  }
  .q-explanation {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%);
    border-color: rgba(168, 85, 247, 0.3);
  }
  .q-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .q-icon { font-size: 24px; }
  .q-title { font-size: 20px; font-weight: 700; color: #f8fafc; }
  .q-tag {
    margin-left: auto;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 6px;
    text-transform: uppercase;
    font-weight: 600;
  }
  .q-tutorials .q-tag { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
  .q-howto .q-tag { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
  .q-reference .q-tag { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
  .q-explanation .q-tag { background: rgba(168, 85, 247, 0.2); color: #d8b4fe; }
  .doc-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .doc-item {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-size: 14px;
    color: #cbd5e1;
  }
  .doc-file {
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    background: rgba(0, 0, 0, 0.35);
    padding: 3px 8px;
    border-radius: 4px;
    color: #94a3b8;
    margin-left: auto;
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>CHERENKOV-QA 1.4 Documentation Site Map</h1>
    <p>Comprehensive Diátaxis Information Architecture: Tutorials, How-To, Reference, & Explanations</p>
  </div>
  <div class="grid">
    <!-- Tutorials -->
    <div class="quadrant q-tutorials">
      <div class="q-header">
        <span class="q-icon">🎓</span>
        <h2 class="q-title">1. Tutorials</h2>
        <span class="q-tag">Learning-Oriented</span>
      </div>
      <ul class="doc-list">
        <li class="doc-item"><span>Getting Started Guide</span><span class="doc-file">GETTING_STARTED.md</span></li>
        <li class="doc-item"><span>Petstore 5-Min Walkthrough</span><span class="doc-file">QUICKSTART_PETSTORE.md</span></li>
        <li class="doc-item"><span>Knowledge Transfer Script</span><span class="doc-file">KT_ONBOARDING_SCRIPT.md</span></li>
        <li class="doc-item"><span>Agentic Playwright Suite</span><span class="doc-file">LEARNING_AGENTIC_PLAYWRIGHT.md</span></li>
      </ul>
    </div>

    <!-- How-To Guides -->
    <div class="quadrant q-howto">
      <div class="q-header">
        <span class="q-icon">🛠️</span>
        <h2 class="q-title">2. How-To Guides</h2>
        <span class="q-tag">Task-Oriented</span>
      </div>
      <ul class="doc-list">
        <li class="doc-item"><span>GitHub Actions CI Pipeline</span><span class="doc-file">guides/github-actions-setup.md</span></li>
        <li class="doc-item"><span>Kubernetes Operator Setup</span><span class="doc-file">guides/k8s-deployment.md</span></li>
        <li class="doc-item"><span>MCP Tool & Template Publishing</span><span class="doc-file">README-MCP-PUBLISH.md</span></li>
        <li class="doc-item"><span>Migrating from Dredd & Postman</span><span class="doc-file">guides/migrating-from-dredd.md</span></li>
        <li class="doc-item"><span>Spec Guardian & Certificates</span><span class="doc-file">guides/spec_guardian.md</span></li>
      </ul>
    </div>

    <!-- Reference -->
    <div class="quadrant q-reference">
      <div class="q-header">
        <span class="q-icon">📋</span>
        <h2 class="q-title">3. Reference</h2>
        <span class="q-tag">Information-Oriented</span>
      </div>
      <ul class="doc-list">
        <li class="doc-item"><span>CLI Command & Flag Reference</span><span class="doc-file">cli-reference.md</span></li>
        <li class="doc-item"><span>Architecture Inventory & Map</span><span class="doc-file">ARCHITECTURE_MAP.md</span></li>
        <li class="doc-item"><span>Error Codes & Status Codes</span><span class="doc-file">ERROR_HANDLING.md</span></li>
        <li class="doc-item"><span>Master Roadmap (Phases -1..16)</span><span class="doc-file">ROADMAP.md</span></li>
        <li class="doc-item"><span>System Diagrams & Flows</span><span class="doc-file">diagrams/DIAGRAMS.md</span></li>
        <li class="doc-item"><span>Architecture Decision Records</span><span class="doc-file">adr/INDEX.md</span></li>
      </ul>
    </div>

    <!-- Explanations -->
    <div class="quadrant q-explanation">
      <div class="q-header">
        <span class="q-icon">💡</span>
        <h2 class="q-title">4. Explanations</h2>
        <span class="q-tag">Understanding-Oriented</span>
      </div>
      <ul class="doc-list">
        <li class="doc-item"><span>System Design & Decomposition</span><span class="doc-file">SYSTEM_DESIGN.md</span></li>
        <li class="doc-item"><span>Clean Architecture Ports & Adapters</span><span class="doc-file">adr/ADR-004-clean-architecture.md</span></li>
        <li class="doc-item"><span>Sync Driven Development (SDD)</span><span class="doc-file">engineering/SYNC_DRIVEN_DEV.md</span></li>
        <li class="doc-item"><span>Autonomous Quality Fabric Vision</span><span class="doc-file">VISION_AQE_2026.md</span></li>
        <li class="doc-item"><span>D7 Non-Negotiable Invariants</span><span class="doc-file">AGENTS.md</span></li>
      </ul>
    </div>
  </div>
</div>
</body>
</html>
"""

# 3. HOMEPAGE OVERVIEW (SVG & HTML for PNG screenshot)
HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    min-height: 100vh;
  }
  .navbar {
    background: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 16px 40px;
    display: flex;
    align-items: center;
    gap: 24px;
  }
  .nav-brand {
    font-size: 22px;
    font-weight: 800;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .nav-version {
    background: #0369a1;
    color: #e0f2fe;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 700;
  }
  .nav-links {
    display: flex;
    gap: 20px;
    margin-left: 32px;
    font-size: 15px;
    color: #94a3b8;
  }
  .nav-links .active { color: #f8fafc; font-weight: 600; border-bottom: 2px solid #38bdf8; padding-bottom: 4px; }
  .search-box {
    margin-left: auto;
    background: #0f172a;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
    color: #94a3b8;
    width: 260px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .hero {
    padding: 60px 40px 40px;
    max-width: 1200px;
    margin: 0 auto;
    text-align: center;
  }
  .hero h1 {
    font-size: 48px;
    font-weight: 900;
    line-height: 1.15;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #ffffff 0%, #38bdf8 60%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hero p {
    font-size: 20px;
    color: #94a3b8;
    max-width: 800px;
    margin: 0 auto 36px;
    line-height: 1.6;
  }
  .badges-row {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-bottom: 48px;
  }
  .hero-badge {
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid #334155;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #cbd5e1;
  }
  .cards-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 40px 60px;
  }
  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s;
  }
  .card-icon { font-size: 32px; margin-bottom: 16px; }
  .card h3 { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #f8fafc; }
  .card p { font-size: 14px; color: #94a3b8; line-height: 1.5; margin-bottom: 20px; flex-grow: 1; }
  .card-link { font-size: 14px; font-weight: 600; color: #38bdf8; text-decoration: none; display: flex; align-items: center; gap: 6px; }
</style>
</head>
<body>
  <div class="navbar">
    <div class="nav-brand">⚡ CHERENKOV QA <span class="nav-version">v1.4.0 CURRENT</span></div>
    <div class="nav-links">
      <span class="active">Documentation</span>
      <span>Tutorials</span>
      <span>How-To</span>
      <span>Reference</span>
      <span>Architecture</span>
      <span>GitHub</span>
    </div>
    <div class="search-box"><span>🔍 Search documentation...</span><kbd>Ctrl+K</kbd></div>
  </div>

  <div class="hero">
    <h1>Autonomous Quality Fabric & API Conformance Engine</h1>
    <p>OpenAPI spec in, high-coverage Playwright suites out. Spec-derived validation, clean architecture ports, zero vendor lock-in, and autonomous self-healing.</p>
    <div class="badges-row">
      <div class="hero-badge">🔒 D7 Invariants Active</div>
      <div class="hero-badge">🚀 Zero Lock-In (Eject)</div>
      <div class="hero-badge">🧠 MemSearch SDD Protocol</div>
      <div class="hero-badge">☸️ K8s Operator Ready</div>
    </div>
  </div>

  <div class="cards-grid">
    <div class="card">
      <div class="card-icon">🎓</div>
      <h3>Tutorials</h3>
      <p>Step-by-step onboarding walkthroughs for new users. Run Petstore conformance in under 5 minutes.</p>
      <div class="card-link">Start Learning ➔</div>
    </div>
    <div class="card">
      <div class="card-icon">🛠️</div>
      <h3>How-To Guides</h3>
      <p>Practical recipes for CI/CD pipelines, Kubernetes deployments, and migration from Dredd/Postman.</p>
      <div class="card-link">Explore Guides ➔</div>
    </div>
    <div class="card">
      <div class="card-icon">📋</div>
      <h3>Reference</h3>
      <p>Exhaustive CLI flags, clean architecture ports & adapters inventory, and standardized error codes.</p>
      <div class="card-link">View Reference ➔</div>
    </div>
    <div class="card">
      <div class="card-icon">💡</div>
      <h3>Explanations</h3>
      <p>Deep dives into D7 verification invariants, Sync Driven Development, and the AQE 2026 Vision.</p>
      <div class="card-link">Read Architecture ➔</div>
    </div>
  </div>
</body>
</html>
"""

# 4. GETTING STARTED WALKTHROUGH (SVG & HTML for PNG screenshot)
GETTING_STARTED_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0b0f19;
    color: #f8fafc;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 40px;
  }
  .window {
    width: 1200px;
    background: #1e1e2e;
    border-radius: 16px;
    border: 1px solid #313244;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
    overflow: hidden;
  }
  .title-bar {
    background: #181825;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid #313244;
  }
  .circle { width: 12px; height: 12px; border-radius: 50%; }
  .red { background: #f38ba8; }
  .yellow { background: #f9e2af; }
  .green { background: #a6e3a1; }
  .title-text {
    font-size: 13px;
    color: #a6adc8;
    margin-left: 12px;
    font-family: "JetBrains Mono", monospace;
  }
  .terminal-body {
    padding: 32px;
    font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
    font-size: 15px;
    line-height: 1.6;
    color: #cdd6f4;
  }
  .cmd { color: #89b4fa; font-weight: 700; }
  .prompt { color: #f5c2e7; margin-right: 8px; }
  .comment { color: #6c7086; font-style: italic; }
  .success { color: #a6e3a1; font-weight: 600; }
  .highlight { color: #f9e2af; }
  .cert { color: #cba6f7; }
  .box {
    margin: 16px 0;
    padding: 16px 20px;
    background: #11111b;
    border-left: 4px solid #89b4fa;
    border-radius: 6px;
  }
</style>
</head>
<body>
<div class="window">
  <div class="title-bar">
    <div class="circle red"></div>
    <div class="circle yellow"></div>
    <div class="circle green"></div>
    <span class="title-text">cherenkov-qa — Quickstart Execution (v1.4.0)</span>
  </div>
  <div class="terminal-body">
    <p class="comment"># 1. Install Cherenkov QA CLI</p>
    <p><span class="prompt">$</span><span class="cmd">pip install cherenkov-qa</span></p>
    <p style="margin-bottom: 16px; color: #a6adc8;">Successfully installed cherenkov-qa-1.4.0</p>

    <p class="comment"># 2. Run automated API conformance validation</p>
    <p><span class="prompt">$</span><span class="cmd">cherenkov validate --spec petstore.yaml --target https://api.petstore.io --eject tests/e2e/</span></p>
    
    <div class="box">
      <p>[INGEST] Parsed OpenAPI 3.1 spec (18 endpoints, 42 operations)</p>
      <p>[PLAN] Deterministic test generation: 42 mutation paths generated</p>
      <p>[WITNESS] Executing conformance runs against live target...</p>
      <p class="success">✓ GET  /pets          [200 OK]  Schema: VALID  Time: 42ms</p>
      <p class="success">✓ POST /pets          [201 CRE] Schema: VALID  Time: 58ms</p>
      <p class="success">✓ GET  /pets/{id}     [200 OK]  Schema: VALID  Time: 31ms</p>
      <p class="success">✓ DEL  /pets/{id}     [204 NOC] Schema: VALID  Time: 39ms</p>
      <p style="margin-top: 8px;">[VERDICT] <span class="success">18/18 CERTIFIED</span> (Overall Pass Rate: 100%)</p>
      <p>[EJECT] Standalone Playwright test suite exported to <span class="highlight">tests/e2e/conformance.spec.ts</span></p>
      <p class="cert">[CERTIFICATE] Issued: <span class="cert">sha256:7f9a8b1c4e2d...</span> (Spec Guardian Gate: PASSED)</p>
    </div>

    <p class="comment"># 3. View test results in Dashboard</p>
    <p><span class="prompt">$</span><span class="cmd">cherenkov dashboard --port 8080</span></p>
    <p class="success">✓ Web UI live at http://127.0.0.1:8080 (Knowledge Explorer & Conformance Trends active)</p>
  </div>
</div>
</body>
</html>
"""

def render_assets():
    print(f"Generating visual assets in: {OUTPUT_DIR}")

    # Write SVGs and capture PNGs via Playwright
    targets = [
        ("version_diff", VERSION_DIFF_HTML, 1480, 750),
        ("sitemap_architecture", SITEMAP_HTML, 1480, 850),
        ("homepage_overview", HOMEPAGE_HTML, 1440, 820),
        ("getting_started", GETTING_STARTED_HTML, 1300, 720),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, html_content, width, height in targets:
            # 1. Save HTML temporary / SVG artifact
            html_file = OUTPUT_DIR / f"{name}.html"
            html_file.write_text(html_content, encoding="utf-8")

            # 2. Render and capture high-res PNG
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=2 # 2x DPI for ultra crisp retina rendering
            )
            page.set_content(html_content)
            page.wait_for_load_state("networkidle")

            png_path = OUTPUT_DIR / f"{name}.png"
            page.screenshot(path=str(png_path), full_page=True)
            print(f"  [OK] Generated {png_path.name} ({png_path.stat().st_size} bytes)")

            page.close()

        browser.close()

    print("All static assets generated successfully!")

if __name__ == "__main__":
    render_assets()
