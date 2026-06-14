import * as vscode from 'vscode';
import * as path from 'path';
import { runCherenkovCommand, autoDetectSpec } from '../api/CherenkovClient';

export async function runGenerate(
  outputChannel: vscode.OutputChannel,
  specUri?: vscode.Uri
): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;
  const config = vscode.workspace.getConfiguration('cherenkov');

  let spec: string;
  if (specUri) {
    spec = path.relative(root, specUri.fsPath);
  } else {
    const configured = config.get<string>('specPath', '');
    spec = configured || autoDetectSpec(root) || '';
  }

  if (!spec) {
    const picked = await vscode.window.showInputBox({
      prompt: 'Path to OpenAPI spec (relative to workspace root)',
      placeHolder: 'e.g. openapi.yaml',
      value: 'stub/openapi.yaml',
    });
    if (!picked) {
      return;
    }
    spec = picked;
  }

  const targetUrl = config.get<string>('targetUrl', 'http://localhost:8000');

  outputChannel.show(true);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Cherenkov: Generating tests from spec…',
      cancellable: true,
    },
    async (_progress, token) => {
      const args = ['validate', '--spec', spec, '--target', targetUrl, '--format', 'text'];
      const result = await runCherenkovCommand(args, outputChannel, root, token);

      if (!token.isCancellationRequested) {
        if (result.exitCode === 0) {
          vscode.window.showInformationMessage('Cherenkov: Tests generated and validated ✓');
        } else {
          vscode.window.showWarningMessage('Cherenkov: Generation complete — review output for findings.');
        }
      }
    }
  );
}
