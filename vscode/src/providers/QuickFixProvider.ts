import * as vscode from 'vscode';

export class CherenkovQuickFixProvider implements vscode.CodeActionProvider {
  provideCodeActions(
    document: vscode.TextDocument,
    _range: vscode.Range,
    context: vscode.CodeActionContext,
    _token: vscode.CancellationToken
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];

    const hasCherenkovDiagnostic = context.diagnostics.some(
      d => d.source === 'cherenkov'
    );

    if (!hasCherenkovDiagnostic) {
      return actions;
    }

    const generateAction = new vscode.CodeAction(
      'Cherenkov: Generate conformance test',
      vscode.CodeActionKind.QuickFix
    );
    generateAction.command = {
      command: 'cherenkov.generateAssertion',
      title: 'Generate Conformance Assertion',
    };
    actions.push(generateAction);

    const driftAction = new vscode.CodeAction(
      'Cherenkov: View drift details',
      vscode.CodeActionKind.QuickFix
    );
    driftAction.command = {
      command: 'cherenkov.viewDrift',
      title: 'View Drift Details',
    };
    actions.push(driftAction);

    return actions;
  }
}