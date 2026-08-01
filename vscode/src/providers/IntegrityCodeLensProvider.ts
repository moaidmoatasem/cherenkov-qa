import * as vscode from 'vscode';
import { fetchIntegrityAudit } from '../api/CherenkovClient';

export class IntegrityCodeLensProvider implements vscode.CodeLensProvider {
  private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

  public refresh(): void {
    this._onDidChangeCodeLenses.fire();
  }

  async provideCodeLenses(document: vscode.TextDocument): Promise<vscode.CodeLens[]> {
    const baseUrl = vscode.workspace.getConfiguration('cherenkov').get<string>('targetUrl', 'http://localhost:8000');
    const format = document.languageId === 'python' ? 'pytest' : 'playwright';
    
    const isTest = document.fileName.includes('.spec.ts') || document.fileName.includes('test_') || document.fileName.includes('_test');
    if (!isTest) return [];

    const result = await fetchIntegrityAudit(baseUrl, document.getText(), format);
    if (!result) return [];

    const lenses: vscode.CodeLens[] = [];
    
    // Top of file lens showing overall verdict
    const topRange = new vscode.Range(0, 0, 0, 0);
    const scorePct = Math.round(result.integrity_score * 100);
    lenses.push(new vscode.CodeLens(topRange, {
      title: `🛡️ Integrity: ${result.verdict} (${scorePct}%)`,
      command: '',
      tooltip: result.summary,
    }));

    // Add lenses for specific issues
    for (const issue of result.issues) {
      if (issue.line) {
        const lineIdx = Math.max(0, issue.line - 1);
        const range = new vscode.Range(lineIdx, 0, lineIdx, 0);
        lenses.push(new vscode.CodeLens(range, {
          title: `⚠ Weak Assertion: ${issue.suggestion}`,
          command: '',
          tooltip: issue.detail,
        }));
      }
    }

    return lenses;
  }
}
