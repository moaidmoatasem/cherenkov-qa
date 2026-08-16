"""
Generates clean, scalable SVG vector assets in docs/1.4/assets/
"""
from pathlib import Path

OUTPUT_DIR = Path("docs/1.4/assets").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VERSION_DIFF_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 650" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e1b4b"/>
    </linearGradient>
    <linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#60a5fa"/>
      <stop offset="50%" stop-color="#a78bfa"/>
      <stop offset="100%" stop-color="#f472b6"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="650" rx="16" fill="url(#bgGrad)" />
  
  <!-- Header -->
  <text x="600" y="55" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="28" font-weight="bold" fill="url(#titleGrad)" text-anchor="middle">CHERENKOV-QA Version Evolution Architecture</text>
  <text x="600" y="85" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="14" fill="#94a3b8" text-anchor="middle">Progression from Foundation (v1.2) through Autonomous Extensions (v1.3) to Consolidated Release (v1.4)</text>

  <!-- V1.2 Card -->
  <g transform="translate(40, 120)">
    <rect width="340" height="470" rx="12" fill="#1e293b" stroke="#64748b" stroke-width="2" />
    <rect x="20" y="20" width="130" height="26" rx="13" fill="#ef4444" fill-opacity="0.2" stroke="#ef4444" stroke-width="1"/>
    <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="bold" fill="#fca5a5" text-anchor="middle">LEGACY / ARCHIVED</text>
    <text x="20" y="75" font-family="sans-serif" font-size="22" font-weight="bold" fill="#f8fafc">Version 1.2</text>
    <text x="20" y="98" font-family="sans-serif" font-size="13" fill="#94a3b8">Core Invariants &amp; Foundations</text>
    <line x1="20" y1="115" x2="320" y2="115" stroke="#334155" stroke-width="1"/>
    
    <circle cx="30" cy="145" r="3" fill="#94a3b8"/>
    <text x="45" y="149" font-family="sans-serif" font-size="13" fill="#cbd5e1">Core API Conformance Engine</text>
    
    <circle cx="30" cy="180" r="3" fill="#94a3b8"/>
    <text x="45" y="184" font-family="sans-serif" font-size="13" fill="#cbd5e1">Playwright Test Generation</text>
    
    <circle cx="30" cy="215" r="3" fill="#94a3b8"/>
    <text x="45" y="219" font-family="sans-serif" font-size="13" fill="#cbd5e1">SQLite Storage (verdicts.db)</text>
    
    <circle cx="30" cy="250" r="3" fill="#94a3b8"/>
    <text x="45" y="254" font-family="sans-serif" font-size="13" fill="#cbd5e1">D7 Non-Negotiable Invariants</text>
    
    <circle cx="30" cy="285" r="3" fill="#94a3b8"/>
    <text x="45" y="289" font-family="sans-serif" font-size="13" fill="#cbd5e1">CLI Baseline (run, validate, eject)</text>

    <line x1="20" y1="415" x2="320" y2="415" stroke="#334155" stroke-width="1"/>
    <text x="20" y="445" font-family="sans-serif" font-size="12" fill="#f87171">⚠️ Outdated warning banner active</text>
  </g>

  <!-- Arrow 1 -->
  <path d="M 395 355 L 420 355" stroke="#64748b" stroke-width="3" marker-end="url(#arrow)" />
  <text x="410" y="340" font-family="sans-serif" font-size="20" fill="#64748b" text-anchor="middle">➔</text>

  <!-- V1.3 Card -->
  <g transform="translate(430, 120)">
    <rect width="340" height="470" rx="12" fill="#1e1b4b" fill-opacity="0.6" stroke="#818cf8" stroke-width="2" />
    <rect x="20" y="20" width="130" height="26" rx="13" fill="#f59e0b" fill-opacity="0.2" stroke="#f59e0b" stroke-width="1"/>
    <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="bold" fill="#fcd34d" text-anchor="middle">PREVIOUS MINOR</text>
    <text x="20" y="75" font-family="sans-serif" font-size="22" font-weight="bold" fill="#f8fafc">Version 1.3</text>
    <text x="20" y="98" font-family="sans-serif" font-size="13" fill="#94a3b8">Autonomous Fabric &amp; Horizons</text>
    <line x1="20" y1="115" x2="320" y2="115" stroke="#3730a3" stroke-width="1"/>
    
    <circle cx="30" cy="145" r="3" fill="#a5b4fc"/>
    <text x="45" y="149" font-family="sans-serif" font-size="13" fill="#cbd5e1">Second Brain (Knowledge Mesh)</text>
    
    <circle cx="30" cy="180" r="3" fill="#a5b4fc"/>
    <text x="45" y="184" font-family="sans-serif" font-size="13" fill="#cbd5e1">VLM + LocalAI Backend Routing</text>
    
    <circle cx="30" cy="215" r="3" fill="#a5b4fc"/>
    <text x="45" y="219" font-family="sans-serif" font-size="13" fill="#cbd5e1">Tauri 2 Desktop Host App</text>
    
    <circle cx="30" cy="250" r="3" fill="#a5b4fc"/>
    <text x="45" y="254" font-family="sans-serif" font-size="13" fill="#cbd5e1">Chat Agent + Persona SSE</text>
    
    <circle cx="30" cy="285" r="3" fill="#a5b4fc"/>
    <text x="45" y="289" font-family="sans-serif" font-size="13" fill="#cbd5e1">Mobile Engine (Maestro/ADB)</text>

    <circle cx="30" cy="320" r="3" fill="#a5b4fc"/>
    <text x="45" y="324" font-family="sans-serif" font-size="13" fill="#cbd5e1">Kubernetes Operator &amp; CRDs</text>

    <line x1="20" y1="415" x2="320" y2="415" stroke="#3730a3" stroke-width="1"/>
    <text x="20" y="445" font-family="sans-serif" font-size="12" fill="#f87171">⚠️ Banner links to /1.4/ release</text>
  </g>

  <!-- Arrow 2 -->
  <text x="800" y="340" font-family="sans-serif" font-size="20" fill="#38bdf8" text-anchor="middle">➔</text>

  <!-- V1.4 Card -->
  <g transform="translate(820, 120)">
    <rect width="340" height="470" rx="12" fill="#0c4a6e" fill-opacity="0.4" stroke="#38bdf8" stroke-width="2.5" />
    <rect x="20" y="20" width="140" height="26" rx="13" fill="#22c55e" fill-opacity="0.25" stroke="#22c55e" stroke-width="1.5"/>
    <text x="90" y="37" font-family="sans-serif" font-size="11" font-weight="bold" fill="#86efac" text-anchor="middle">CURRENT / LATEST</text>
    <text x="20" y="75" font-family="sans-serif" font-size="22" font-weight="bold" fill="#f8fafc">Version 1.4.0</text>
    <text x="20" y="98" font-family="sans-serif" font-size="13" fill="#38bdf8">Consolidated Release Hub</text>
    <line x1="20" y1="115" x2="320" y2="115" stroke="#0284c7" stroke-width="1"/>
    
    <circle cx="30" cy="145" r="3" fill="#38bdf8"/>
    <text x="45" y="149" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Unified 1.4 Diátaxis Structure</text>
    
    <circle cx="30" cy="180" r="3" fill="#38bdf8"/>
    <text x="45" y="184" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Clean Architecture (ADR-004)</text>
    
    <circle cx="30" cy="215" r="3" fill="#38bdf8"/>
    <text x="45" y="219" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">MemSearch SDD Memory Layer</text>
    
    <circle cx="30" cy="250" r="3" fill="#38bdf8"/>
    <text x="45" y="254" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Multi-Agent Conductor (CC-1..6)</text>
    
    <circle cx="30" cy="285" r="3" fill="#38bdf8"/>
    <text x="45" y="289" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Native CI/CD &amp; Jenkins Library</text>

    <circle cx="30" cy="320" r="3" fill="#38bdf8"/>
    <text x="45" y="324" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Spec Guardian &amp; Certificates</text>

    <circle cx="30" cy="355" r="3" fill="#38bdf8"/>
    <text x="45" y="359" font-family="sans-serif" font-size="13" font-weight="bold" fill="#f8fafc">Live Conformance Trend &amp; Maps</text>

    <line x1="20" y1="415" x2="320" y2="415" stroke="#0284c7" stroke-width="1"/>
    <text x="20" y="445" font-family="sans-serif" font-size="12" font-weight="bold" fill="#4ade80">✅ Authoritative (No warning banner)</text>
  </g>
</svg>
"""

SITEMAP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 700" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad2" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b0f19"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="700" rx="16" fill="url(#bgGrad2)" />

  <text x="600" y="48" font-family="sans-serif" font-size="26" font-weight="bold" fill="#38bdf8" text-anchor="middle">CHERENKOV-QA 1.4 Documentation Site Map</text>
  <text x="600" y="74" font-family="sans-serif" font-size="14" fill="#94a3b8" text-anchor="middle">Diátaxis Documentation Architecture: Tutorials, How-To Guides, Reference, &amp; Explanations</text>

  <!-- Quadrant 1: Tutorials -->
  <g transform="translate(40, 100)">
    <rect width="540" height="260" rx="12" fill="#064e3b" fill-opacity="0.25" stroke="#059669" stroke-width="1.5"/>
    <text x="24" y="36" font-family="sans-serif" font-size="20">🎓</text>
    <text x="56" y="36" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f8fafc">1. Tutorials</text>
    <rect x="420" y="18" width="100" height="22" rx="4" fill="#059669" fill-opacity="0.3"/>
    <text x="470" y="33" font-family="sans-serif" font-size="10" font-weight="bold" fill="#6ee7b7" text-anchor="middle">LEARNING</text>
    <line x1="20" y1="52" x2="520" y2="52" stroke="#065f46" stroke-width="1"/>

    <text x="24" y="82" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Getting Started Guide</text>
    <text x="516" y="82" font-family="monospace" font-size="11" fill="#6ee7b7" text-anchor="end">GETTING_STARTED.md</text>

    <text x="24" y="118" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Petstore 5-Min Walkthrough</text>
    <text x="516" y="118" font-family="monospace" font-size="11" fill="#6ee7b7" text-anchor="end">QUICKSTART_PETSTORE.md</text>

    <text x="24" y="154" font-family="sans-serif" font-size="14" fill="#cbd5e1">• KT Onboarding Script</text>
    <text x="516" y="154" font-family="monospace" font-size="11" fill="#6ee7b7" text-anchor="end">KT_ONBOARDING_SCRIPT.md</text>

    <text x="24" y="190" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Agentic Playwright Guide</text>
    <text x="516" y="190" font-family="monospace" font-size="11" fill="#6ee7b7" text-anchor="end">LEARNING_AGENTIC_PLAYWRIGHT.md</text>
  </g>

  <!-- Quadrant 2: How-To Guides -->
  <g transform="translate(620, 100)">
    <rect width="540" height="260" rx="12" fill="#78350f" fill-opacity="0.25" stroke="#d97706" stroke-width="1.5"/>
    <text x="24" y="36" font-family="sans-serif" font-size="20">🛠️</text>
    <text x="56" y="36" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f8fafc">2. How-To Guides</text>
    <rect x="420" y="18" width="100" height="22" rx="4" fill="#d97706" fill-opacity="0.3"/>
    <text x="470" y="33" font-family="sans-serif" font-size="10" font-weight="bold" fill="#fcd34d" text-anchor="middle">TASK-BASED</text>
    <line x1="20" y1="52" x2="520" y2="52" stroke="#92400e" stroke-width="1"/>

    <text x="24" y="82" font-family="sans-serif" font-size="14" fill="#cbd5e1">• GitHub Actions CI Pipeline</text>
    <text x="516" y="82" font-family="monospace" font-size="11" fill="#fcd34d" text-anchor="end">guides/github-actions-setup.md</text>

    <text x="24" y="118" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Kubernetes Operator Deployment</text>
    <text x="516" y="118" font-family="monospace" font-size="11" fill="#fcd34d" text-anchor="end">guides/k8s-deployment.md</text>

    <text x="24" y="154" font-family="sans-serif" font-size="14" fill="#cbd5e1">• MCP Tool &amp; Template Publishing</text>
    <text x="516" y="154" font-family="monospace" font-size="11" fill="#fcd34d" text-anchor="end">README-MCP-PUBLISH.md</text>

    <text x="24" y="190" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Migrating from Dredd / Postman</text>
    <text x="516" y="190" font-family="monospace" font-size="11" fill="#fcd34d" text-anchor="end">guides/migrating-from-dredd.md</text>
  </g>

  <!-- Quadrant 3: Reference -->
  <g transform="translate(40, 390)">
    <rect width="540" height="270" rx="12" fill="#1e3a8a" fill-opacity="0.25" stroke="#2563eb" stroke-width="1.5"/>
    <text x="24" y="36" font-family="sans-serif" font-size="20">📋</text>
    <text x="56" y="36" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f8fafc">3. Reference</text>
    <rect x="420" y="18" width="100" height="22" rx="4" fill="#2563eb" fill-opacity="0.3"/>
    <text x="470" y="33" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93c5fd" text-anchor="middle">INFORMATION</text>
    <line x1="20" y1="52" x2="520" y2="52" stroke="#1e40af" stroke-width="1"/>

    <text x="24" y="82" font-family="sans-serif" font-size="14" fill="#cbd5e1">• CLI Command Reference</text>
    <text x="516" y="82" font-family="monospace" font-size="11" fill="#93c5fd" text-anchor="end">cli-reference.md</text>

    <text x="24" y="118" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Architecture &amp; Ports Map</text>
    <text x="516" y="118" font-family="monospace" font-size="11" fill="#93c5fd" text-anchor="end">ARCHITECTURE_MAP.md</text>

    <text x="24" y="154" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Standard Error &amp; Exit Codes</text>
    <text x="516" y="154" font-family="monospace" font-size="11" fill="#93c5fd" text-anchor="end">ERROR_HANDLING.md</text>

    <text x="24" y="190" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Master Roadmap (Phases -1..16)</text>
    <text x="516" y="190" font-family="monospace" font-size="11" fill="#93c5fd" text-anchor="end">ROADMAP.md</text>

    <text x="24" y="226" font-family="sans-serif" font-size="14" fill="#cbd5e1">• System Diagrams &amp; Flows</text>
    <text x="516" y="226" font-family="monospace" font-size="11" fill="#93c5fd" text-anchor="end">diagrams/DIAGRAMS.md</text>
  </g>

  <!-- Quadrant 4: Explanations -->
  <g transform="translate(620, 390)">
    <rect width="540" height="270" rx="12" fill="#581c87" fill-opacity="0.25" stroke="#9333ea" stroke-width="1.5"/>
    <text x="24" y="36" font-family="sans-serif" font-size="20">💡</text>
    <text x="56" y="36" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f8fafc">4. Explanations</text>
    <rect x="420" y="18" width="100" height="22" rx="4" fill="#9333ea" fill-opacity="0.3"/>
    <text x="470" y="33" font-family="sans-serif" font-size="10" font-weight="bold" fill="#d8b4fe" text-anchor="middle">UNDERSTANDING</text>
    <line x1="20" y1="52" x2="520" y2="52" stroke="#6b21a8" stroke-width="1"/>

    <text x="24" y="82" font-family="sans-serif" font-size="14" fill="#cbd5e1">• System Design &amp; Decomposition</text>
    <text x="516" y="82" font-family="monospace" font-size="11" fill="#d8b4fe" text-anchor="end">SYSTEM_DESIGN.md</text>

    <text x="24" y="118" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Clean Architecture (ADR-004)</text>
    <text x="516" y="118" font-family="monospace" font-size="11" fill="#d8b4fe" text-anchor="end">adr/ADR-004-clean-architecture.md</text>

    <text x="24" y="154" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Sync Driven Development (SDD)</text>
    <text x="516" y="154" font-family="monospace" font-size="11" fill="#d8b4fe" text-anchor="end">engineering/SYNC_DRIVEN_DEV.md</text>

    <text x="24" y="190" font-family="sans-serif" font-size="14" fill="#cbd5e1">• Autonomous Quality Fabric Vision</text>
    <text x="516" y="190" font-family="monospace" font-size="11" fill="#d8b4fe" text-anchor="end">VISION_AQE_2026.md</text>

    <text x="24" y="226" font-family="sans-serif" font-size="14" fill="#cbd5e1">• D7 Validation Invariants</text>
    <text x="516" y="226" font-family="monospace" font-size="11" fill="#d8b4fe" text-anchor="end">AGENTS.md</text>
  </g>
</svg>
"""

(OUTPUT_DIR / "version_diff.svg").write_text(VERSION_DIFF_SVG, encoding="utf-8")
(OUTPUT_DIR / "sitemap_architecture.svg").write_text(SITEMAP_SVG, encoding="utf-8")
print("SVGs written successfully!")
