import React from 'react';
import './index.css';

function App() {
  return (
    <div className="app-container">
      <header className="header">
        <div className="logo">☢️ CHERENKOV-QA</div>
        <nav className="nav">
          <a href="#features">Features</a>
          <a href="https://docs.cherenkov.dev">Docs</a>
          <a href="https://github.com/moaidmoatasem/cherenkov-qa">GitHub</a>
        </nav>
      </header>

      <main className="main-content">
        <section className="hero">
          <div className="hero-badge">v1.0.0 is live!</div>
          <h1 className="hero-title">
            The AI-Native <span className="highlight">API Conformance</span> Platform
          </h1>
          <p className="hero-subtitle">
            Every API has an OpenAPI spec, but they silently drift from the real server implementations every day. 
            CHERENKOV automatically generates typed Playwright tests to catch drift before it hits production.
          </p>
          
          <div className="hero-actions">
            <div className="code-block">
              <code>npx cherenkov init</code>
            </div>
            <a href="https://docs.cherenkov.dev" className="btn-primary">View Documentation</a>
          </div>
        </section>

        <section id="features" className="features">
          <h2 className="section-title">Stop Spec Drift. Zero Lock-in.</h2>
          <div className="feature-grid">
            <div className="feature-card glass-card">
              <div className="feature-icon">🛡️</div>
              <h3>Catch Spec Drift Automatically</h3>
              <p>CHERENKOV generates tests to ensure your backend honors the OpenAPI spec. If the spec says 422 and the server returns 400, we catch it.</p>
            </div>
            
            <div className="feature-card glass-card">
              <div className="feature-icon">🧠</div>
              <h3>Hallucination-Resistant</h3>
              <p>The LLM writes the test structure, but the expected values are derived strictly from your spec. Real assertions, zero AI hallucinations.</p>
            </div>

            <div className="feature-card glass-card">
              <div className="feature-icon">🔓</div>
              <h3>Eject Anytime</h3>
              <p>Zero vendor lock-in. Eject the generated tests into standard Playwright code at any time. Your tests run perfectly without us.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <p>© 2026 CHERENKOV-QA. Built for developers who hate manual API testing.</p>
      </footer>
    </div>
  );
}

export default App;
