import * as vscode from 'vscode';

interface ReportFinding {
  endpoint: string;
  status: string;
  message?: string;
}

export class CherenkovDiagnosticsProvider {
  private collection: vscode.DiagnosticCollection;

  constructor() {
    this.collection = vscode.languages.createDiagnosticCollection('cherenkov');
  }

  updateDiagnostics(document: vscode.TextDocument, report: { findings: ReportFinding[] } | null): void {
    this.collection.delete(document.uri);

    if (!report || !report.findings) {
      return;
    }

    const text = document.getText();
    if (!text.includes('openapi:') && !text.includes('"openapi"')) {
      return;
    }

    const lines = text.split('\n');
    const diagnostics: vscode.Diagnostic[] = [];

    for (const finding of report.findings) {
      if (finding.status !== 'FAIL' && finding.status !== 'DRIFT') {
        continue;
      }

      const severity = finding.status === 'FAIL'
        ? vscode.DiagnosticSeverity.Error
        : vscode.DiagnosticSeverity.Warning;

      let lineIndex = lines.findIndex(line => {
        const trimmed = line.trim();
        return trimmed.startsWith(finding.endpoint) || trimmed.startsWith(`"${finding.endpoint}"`);
      });

      if (lineIndex === -1) {
        lineIndex = lines.findIndex(line => line.includes(finding.endpoint));
      }

      if (lineIndex === -1) {
        continue;
      }

      const lineLength = lines[lineIndex].length;
      const range = new vscode.Range(lineIndex, 0, lineIndex, lineLength);
      const message = finding.message
        ? `${finding.status}: ${finding.endpoint} — ${finding.message}`
        : `${finding.status}: ${finding.endpoint}`;

      const diagnostic = new vscode.Diagnostic(range, message, severity);
      diagnostic.source = 'cherenkov';
      diagnostics.push(diagnostic);
    }

    this.collection.set(document.uri, diagnostics);
  }

  dispose(): void {
    this.collection.dispose();
  }
}