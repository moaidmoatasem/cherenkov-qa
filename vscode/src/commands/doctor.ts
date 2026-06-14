import * as vscode from 'vscode';
import { runCherenkovCommand } from '../api/CherenkovClient';

export async function runDoctor(outputChannel: vscode.OutputChannel): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;

  outputChannel.show(true);
  outputChannel.appendLine('Cherenkov: Running environment health check…');

  const result = await runCherenkovCommand(['doctor'], outputChannel, root);

  if (result.exitCode === 0) {
    vscode.window.showInformationMessage('Cherenkov: Environment is healthy ✓');
  } else {
    vscode.window.showWarningMessage(
      'Cherenkov: Some environment checks failed — see output for details.',
      'Show Output'
    ).then(action => {
      if (action === 'Show Output') {
        outputChannel.show(true);
      }
    });
  }
}

export async function runInit(outputChannel: vscode.OutputChannel): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;

  outputChannel.show(true);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Cherenkov: Initializing project…',
      cancellable: false,
    },
    async () => {
      const result = await runCherenkovCommand(['init'], outputChannel, root);
      if (result.exitCode === 0) {
        vscode.window.showInformationMessage('Cherenkov: Project initialized ✓ — run "Cherenkov: Check Environment Health" to verify.');
      } else {
        vscode.window.showWarningMessage('Cherenkov: Init completed with warnings — see output panel.');
      }
    }
  );
}
