import * as vscode from 'vscode';
import * as path from 'path';

interface ReportFinding {
  endpoint: string;
  status: string;
  message?: string;
}

export class CherenkovHoverProvider implements vscode.HoverProvider {
  private report: { findings: ReportFinding[] } | null = null;

  constructor(report: { findings: ReportFinding[] } | null = null) {
    this.report = report;
  }

  setReport(report: { findings: ReportFinding[] } | null): void {
    this.report = report;
  }

  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position,
    _token: vscode.CancellationToken
  ): vscode.Hover | null {
    const ext = path.extname(document.uri.fsPath).toLowerCase();
    if (ext !== '.yaml' && ext !== '.yml' && ext !== '.json') {
      return null;
    }

    const text = document.getText();
    if (!text.includes('openapi:') && !text.includes('"openapi"')) {
      return null;
    }

    if (!this.report || !this.report.findings) {
      return null;
    }

    const line = document.lineAt(position.line).text;
    const match = line.match(/^\s*(\/[^\s:]+)/);
    if (!match) {
      return null;
    }

    const endpoint = match[1];
    const findings = this.report.findings.filter(f => f.endpoint === endpoint);
    if (findings.length === 0) {
      return null;
    }

    const lines: string[] = [`**${endpoint}**`];
    for (const f of findings) {
      const statusLabel = f.status === 'PASS' ? '✓ PASS' : f.status === 'FAIL' ? '✗ FAIL' : '⚠ DRIFT';
      lines.push(`${statusLabel}${f.message ? ` — ${f.message}` : ''}`);
    }

    const range = new vscode.Range(position.line, 0, position.line, line.length);
    return new vscode.Hover(new vscode.MarkdownString(lines.join('\n\n')), range);
  }
}