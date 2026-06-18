import * as vscode from 'vscode';

const OPENAPI_PATH_RE = /^(  |\t)(\/[^\s:]+)\s*:/m;

export class CherenkovCodeLensProvider implements vscode.CodeLensProvider {
  private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

  private report: { findings: Array<{ endpoint: string }> } | null = null;

  setReport(report: { findings: Array<{ endpoint: string }> } | null): void {
    this.report = report;
    this._onDidChangeCodeLenses.fire();
  }

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const lenses: vscode.CodeLens[] = [];
    const text = document.getText();

    // Only activate on OpenAPI documents
    if (!text.includes('openapi:') && !text.includes('"openapi"')) {
      return lenses;
    }

    // Find "paths:" section
    const pathsIdx = text.indexOf('\npaths:');
    if (pathsIdx === -1) {
      return lenses;
    }

    // Scan lines after "paths:" for path entries
    const lines = text.split('\n');
    let inPaths = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === 'paths:') {
        inPaths = true;
        continue;
      }
      if (!inPaths) {
        continue;
      }
      // Top-level path entry (2 spaces or 1 tab indent, starts with /)
      if (/^(  |\t)\//.test(line)) {
        const pathMatch = line.match(/^\s*(\/[^\s:]+)/);
        if (!pathMatch) {
          continue;
        }
        const endpoint = pathMatch[1];
        const range = new vscode.Range(i, 0, i, line.length);

        // Count findings for this endpoint
        const findings = this.report?.findings.filter(f => f.endpoint === endpoint) ?? [];
        const driftCount = findings.length;

        const validateLens = new vscode.CodeLens(range, {
          title: driftCount > 0 ? `⚠ ${driftCount} drift violation${driftCount > 1 ? 's' : ''}` : '▶ Run conformance tests',
          command: 'cherenkov.validate',
          tooltip: driftCount > 0
            ? `${driftCount} conformance violation(s) detected on ${endpoint}`
            : `Run Cherenkov conformance tests`,
        });
        lenses.push(validateLens);

        if (driftCount > 0) {
          const healLens = new vscode.CodeLens(range, {
            title: '→ Heal',
            command: 'editor.action.quickFix',
            arguments: [document.uri, range],
            tooltip: 'Show suggested fixes for drift violations',
          });
          lenses.push(healLens);
        }
      }
      // Stop when we hit a top-level key that isn't paths content
      if (/^\S/.test(line) && line.trim() !== 'paths:') {
        inPaths = false;
      }
    }

    return lenses;
  }
}
