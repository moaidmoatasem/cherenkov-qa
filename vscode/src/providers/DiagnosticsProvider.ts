import * as vscode from 'vscode';
import { ConformanceReport } from '../api/CherenkovClient';

export class CherenkovDiagnosticsProvider {
  private collection: vscode.DiagnosticCollection;

  constructor() {
    this.collection = vscode.languages.createDiagnosticCollection('cherenkov');
  }

  updateDiagnostics(document: vscode.TextDocument, report: ConformanceReport | null): void {
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
      if (finding.severity !== 'high') {
        continue;
      }

      const severity = vscode.DiagnosticSeverity.Error;

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
      const message = `FAIL: ${finding.endpoint} — expected: ${finding.expected}, actual: ${finding.actual}`;

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
