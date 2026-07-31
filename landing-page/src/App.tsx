import React, { useState, useEffect } from 'react';
import './index.css';

const TERMINAL_LINES = [
  { delay: 0,    text: '$ cherenkov init', type: 'cmd' },
  { delay: 400,  text: '[OK] Python 3.11 detected', type: 'ok' },
  { delay: 700,  text: '[OK] Installing cherenkov-qa...', type: 'ok' },
  { delay: 1200, text: '[OK] Config created at .cherenkov/', type: 'ok' },
  { delay: 1600, text: '', type: 'blank' },
  { delay: 1700, text: '$ cherenkov validate --spec openapi.yaml --target http://localhost:8000', type: 'cmd' },
  { delay: 2200, text: 'Generating 47 conformance tests from spec...', type: 'info' },
  { delay: 2800, text: 'Running against http://localhost:8000...', type: 'info' },
  { delay: 3400, text: '', type: 'blank' },
  { delay: 3500, text: '[DRIFT] POST /users — expected 422, got 400', type: 'drift' },
  { delay: 3700, text: '[DRIFT] GET /orders/{id} — required field "status" missing', type: 'drift' },
  { delay: 3900, text: '', type: 'blank' },
  { delay: 4000, text: 'Verdict: DRIFT DETECTED (2 violations / 47 tests)', type: 'result' },
];

function TerminalDemo() {
  const [lines, setLines] = useState<typeof TERMINAL_LINES>([]);

  useEffect(() => {
    const timers = TERMINAL_LINES.map((line) =>
      setTimeout(() => setLines((prev) => [...prev, line]), line.delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="terminal">
      <div className="terminal-header">
        <span className="dot red" /><span className="dot yellow" /><span className="dot green" />
        <span className="terminal-title">cherenkov — bash</span>
      </div>
      <div className="terminal-body">
        {lines.map((line, i) =>
          line.type === 'blank' ? <br key={i} /> : (
            <div key={i} className={`line line-${line.type}`}>
              {line.text}
            </div>
          )
        )}
        <span className="cursor">█</span>
      </div>
    </div>
  );
}

const FEATURES = [
  { icon: '🛡️', title: 'Catch Spec Drift Automatically', desc: 'CHERENKOV runs spec-derived tests against your real server every commit. If the spec says 422 and the server returns 400, you know before production does.' },
  { icon: '🧠', title: 'Hallucination-Resistant by Architecture', desc: 'The LLM writes test structure. Expected values come strictly from your OpenAPI spec. No guessing. No false positives.' },
  { icon: '🔓', title: 'Zero Vendor Lock-In', desc: 'One command ejects everything into standard Playwright code. Your tests run perfectly without CHERENKOV. We earn every renewal.' },
  { icon: '🏠', title: 'Local-First. Privacy-Safe.', desc: 'Default LLM is Ollama (qwen2.5-coder:7b). Your specs never leave your machine. OpenAI is an opt-in fallback.' },
  { icon: '⚡', title: 'CI/CD Native', desc: 'GitHub Action, Docker image, K8s CRD operator. One line in your workflow catches drift before any merge.' },
  { icon: '🔗', title: 'LangChain + MCP Ecosystem', desc: 'Expose CHERENKOV as LangChain tools or an MCP server. Drop AI agents into your API testing loop.' },
];

const STEPS = [
  { num: '01', title: 'Initialize', code: 'npx cherenkov init', desc: 'Detects Python, installs CHERENKOV, creates your project config.' },
  { num: '02', title: 'Validate', code: 'cherenkov validate --spec openapi.yaml --target http://localhost:8000', desc: 'Generates typed Playwright tests from your spec, runs them, reports drift.' },
  { num: '03', title: 'Review', code: 'cherenkov doctor --open', desc: 'Dashboard opens with findings, severity, healing suggestions, and eject option.' },
];

function App() {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText('npx cherenkov init');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="app">
      {/* NAV */}
      <nav className="nav">
        <div className="nav-inner">
          <a href="/" className="logo">☢️ CHERENKOV</a>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#quickstart">Quickstart</a>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa" target="_blank" rel="noreferrer">GitHub</a>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa/releases" className="btn-nav" target="_blank" rel="noreferrer">v1.1.1</a>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero">
        <div className="hero-inner">
          <div className="badge">
            <span className="badge-dot" />
            Open Source · Apache 2.0 · Local-First AI
          </div>
          <h1>
            Your API spec is lying.<br />
            <span className="gradient-text">We prove it.</span>
          </h1>
          <p className="hero-sub">
            CHERENKOV generates typed Playwright conformance tests from your OpenAPI spec and runs
            them against your real server — catching spec drift before it reaches production.
          </p>
          <div className="hero-cta">
            <div className="copy-block" onClick={copy}>
              <span className="copy-prompt">$</span>
              <code>npx cherenkov init</code>
              <span className="copy-icon">{copied ? '✓' : '⧉'}</span>
            </div>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa" className="btn-primary" target="_blank" rel="noreferrer">
              View on GitHub →
            </a>
          </div>
          <div className="hero-stats">
            <div className="stat"><strong>47+</strong><span>Tests generated per spec</span></div>
            <div className="stat-divider" />
            <div className="stat"><strong>0</strong><span>Vendor lock-in</span></div>
            <div className="stat-divider" />
            <div className="stat"><strong>100%</strong><span>Local LLM capable</span></div>
          </div>
        </div>
        <div className="hero-demo">
          <TerminalDemo />
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="section">
        <div className="section-inner">
          <p className="section-label">CAPABILITIES</p>
          <h2>Stop shipping spec drift.</h2>
          <p className="section-sub">Everything you need to keep your API honest, with zero ceremony.</p>
          <div className="feature-grid">
            {FEATURES.map((f) => (
              <div className="feature-card" key={f.title}>
                <div className="feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* QUICKSTART */}
      <section id="quickstart" className="section section-dark">
        <div className="section-inner">
          <p className="section-label">QUICKSTART</p>
          <h2>Zero to conformance in 3 commands.</h2>
          <div className="steps">
            {STEPS.map((s) => (
              <div className="step" key={s.num}>
                <div className="step-num">{s.num}</div>
                <div className="step-body">
                  <h3>{s.title}</h3>
                  <code className="step-code">{s.code}</code>
                  <p>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CI BADGE SECTION */}
      <section className="section">
        <div className="section-inner text-center">
          <p className="section-label">GITHUB ACTIONS</p>
          <h2>One line in CI. Infinite confidence.</h2>
          <p className="section-sub">Add the CHERENKOV action to any workflow — catches drift before merge.</p>
          <div className="code-block-wide">
            <pre>{`- uses: moaidmoatasem/cherenkov-qa@v1
  with:
    spec: openapi.yaml
    target: http://your-api
    fail-on-drift: true`}</pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="cta-inner">
          <h2>Start catching drift today.</h2>
          <p>Open source. Apache 2.0. No account required.</p>
          <div className="hero-cta">
            <div className="copy-block" onClick={copy}>
              <span className="copy-prompt">$</span>
              <code>npx cherenkov init</code>
              <span className="copy-icon">{copied ? '✓' : '⧉'}</span>
            </div>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa" className="btn-primary" target="_blank" rel="noreferrer">
              Star on GitHub →
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <div className="footer-inner">
          <span className="logo">☢️ CHERENKOV</span>
          <div className="footer-links">
            <a href="https://github.com/moaidmoatasem/cherenkov-qa" target="_blank" rel="noreferrer">GitHub</a>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa/blob/main/LICENSE" target="_blank" rel="noreferrer">License</a>
            <a href="https://github.com/moaidmoatasem/cherenkov-qa/blob/main/SECURITY.md" target="_blank" rel="noreferrer">Security</a>
          </div>
          <span className="footer-copy">Apache 2.0 · Built for developers who hate spec drift</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
