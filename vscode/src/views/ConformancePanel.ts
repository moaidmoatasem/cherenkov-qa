import * as vscode from 'vscode';
import { ConformanceReport } from '../api/CherenkovClient';

export class ConformancePanel {
  static currentPanel: ConformancePanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private _disposables: vscode.Disposable[] = [];

  static createOrShow(extensionUri: vscode.Uri, report?: ConformanceReport | null): void {
    const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;

    if (ConformancePanel.currentPanel) {
      ConformancePanel.currentPanel._panel.reveal(column);
      if (report !== undefined) {
        ConformancePanel.currentPanel._update(report);
      }
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'cherenkovConformance',
      'Cherenkov — Conformance Report',
      column,
      { enableScripts: true, retainContextWhenHidden: true }
    );

    ConformancePanel.currentPanel = new ConformancePanel(panel, extensionUri);
    if (report !== undefined) {
      ConformancePanel.currentPanel._update(report);
    }
  }

  private constructor(panel: vscode.WebviewPanel, _extensionUri: vscode.Uri) {
    this._panel = panel;
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    this._panel.webview.html = this._getLoadingHtml();
  }

  private _update(report: ConformanceReport | null): void {
    this._panel.webview.html = report ? this._getReportHtml(report) : this._getEmptyHtml();
  }

  private _getLoadingHtml(): string {
    return `<!DOCTYPE html><html><body style="font-family:monospace;padding:2rem;color:#ccc;background:#0d1117">
      <p>Loading conformance report…</p>
    </body></html>`;
  }

  private _getEmptyHtml(): string {
    return `<!DOCTYPE html><html><body style="font-family:monospace;padding:2rem;color:#ccc;background:#0d1117">
      <h2 style="color:#58a6ff">⚡ CHERENKOV QA</h2>
      <p>No report yet. Run <strong>Cherenkov: Run Conformance Tests</strong> to generate one.</p>
    </body></html>`;
  }

  private _getReportHtml(report: ConformanceReport): string {
    const statusColor = report.failed === 0 ? '#3fb950' : '#f85149';
    const findings = (report.findings ?? []).map(f => `
      <tr style="border-top:1px solid #30363d">
        <td style="padding:8px;color:#58a6ff">${f.method ?? ''}</td>
        <td style="padding:8px">${f.endpoint ?? ''}</td>
        <td style="padding:8px;color:${f.severity === 'high' ? '#f85149' : f.severity === 'medium' ? '#d29922' : '#8b949e'}">${f.severity ?? ''}</td>
        <td style="padding:8px;color:#8b949e">${f.expected ?? ''}</td>
        <td style="padding:8px;color:#f85149">${f.actual ?? ''}</td>
      </tr>`).join('');

    return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>
  body{font-family:monospace;padding:2rem;color:#e6edf3;background:#0d1117;margin:0}
  h2{color:#58a6ff}
  .summary{display:flex;gap:2rem;margin:1rem 0 2rem}
  .stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1rem 1.5rem;text-align:center}
  .stat-num{font-size:2rem;font-weight:bold}
  .pass{color:#3fb950}.fail{color:#f85149}.drift{color:#d29922}
  table{width:100%;border-collapse:collapse;font-size:0.85rem}
  th{text-align:left;padding:8px;color:#8b949e;border-bottom:1px solid #30363d}
</style></head>
<body>
<h2>⚡ CHERENKOV — Conformance Report</h2>
<div class="summary">
  <div class="stat"><div class="stat-num pass">${report.passed}</div><div>PASSED</div></div>
  <div class="stat"><div class="stat-num fail">${report.failed}</div><div>FAILED</div></div>
  <div class="stat"><div class="stat-num drift">${report.driftCount}</div><div>DRIFT</div></div>
</div>
${report.findings?.length ? `
<table>
  <thead><tr>
    <th>Method</th><th>Endpoint</th><th>Severity</th><th>Expected</th><th>Actual</th>
  </tr></thead>
  <tbody>${findings}</tbody>
</table>` : `<p style="color:#3fb950">✓ No conformance violations detected.</p>`}
</body></html>`;
  }

  dispose(): void {
    ConformancePanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      this._disposables.pop()?.dispose();
    }
  }
}
