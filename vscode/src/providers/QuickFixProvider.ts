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

    const healAction = new vscode.CodeAction(
      'Cherenkov: Apply suggested assertion (Suggest-only)',
      vscode.CodeActionKind.QuickFix
    );
    healAction.command = {
      command: 'cherenkov.applySuggestedAssertion',
      title: 'Apply Suggested Assertion',
      arguments: [context.diagnostics[0].message] // Pass the diagnostic message to the command
    };
    actions.push(healAction);

    return actions;
  }
}
