import * as vscode from 'vscode';
import { ConformanceReport } from '../api/CherenkovClient';

const SVG_PASS = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="%232ea043"/></svg>`;
const SVG_FAIL = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="%23f85149"/></svg>`;
const SVG_UNTESTED = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="%238b949e"/></svg>`;

export class CherenkovGutterProvider {
  private passDecoration: vscode.TextEditorDecorationType;
  private failDecoration: vscode.TextEditorDecorationType;
  private untestedDecoration: vscode.TextEditorDecorationType;

  constructor() {
    this.passDecoration = vscode.window.createTextEditorDecorationType({
      gutterIconPath: vscode.Uri.parse(SVG_PASS),
      gutterIconSize: 'contain',
    });
    this.failDecoration = vscode.window.createTextEditorDecorationType({
      gutterIconPath: vscode.Uri.parse(SVG_FAIL),
      gutterIconSize: 'contain',
    });
    this.untestedDecoration = vscode.window.createTextEditorDecorationType({
      gutterIconPath: vscode.Uri.parse(SVG_UNTESTED),
      gutterIconSize: 'contain',
    });
  }

  updateDecorations(editor: vscode.TextEditor, report: ConformanceReport | null): void {
    if (!editor.document.getText().includes('openapi:') && !editor.document.getText().includes('"openapi"')) {
      return;
    }

    const text = editor.document.getText();
    const pathsIdx = text.indexOf('\npaths:');
    if (pathsIdx === -1) {
      return;
    }

    const lines = text.split('\n');
    let inPaths = false;

    const passRanges: vscode.Range[] = [];
    const failRanges: vscode.Range[] = [];
    const untestedRanges: vscode.Range[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === 'paths:') {
        inPaths = true;
        continue;
      }
      if (!inPaths) {continue;}

      if (/^(  |\t)\//.test(line)) {
        const pathMatch = line.match(/^\s*(\/[^\s:]+)/);
        if (!pathMatch) {continue;}
        const endpoint = pathMatch[1];
        const range = new vscode.Range(i, 0, i, line.length);

        if (!report) {
          untestedRanges.push(range);
          continue;
        }

        const findings = report.findings?.filter(f => f.endpoint === endpoint) ?? [];
        // Determine status from tests
        // If we have findings with severity 'high', it's a fail
        const hasFailures = findings.some(f => f.severity === 'high');
        
        const wasTested = findings.length > 0;

        if (hasFailures) {
          failRanges.push(range);
        } else if (wasTested) {
          passRanges.push(range);
        } else {
          untestedRanges.push(range);
        }
      }

      if (/^\S/.test(line) && line.trim() !== 'paths:') {
        inPaths = false;
      }
    }

    editor.setDecorations(this.passDecoration, passRanges);
    editor.setDecorations(this.failDecoration, failRanges);
    editor.setDecorations(this.untestedDecoration, untestedRanges);
  }

  dispose(): void {
    this.passDecoration.dispose();
    this.failDecoration.dispose();
    this.untestedDecoration.dispose();
  }
}
