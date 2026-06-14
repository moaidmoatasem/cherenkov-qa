import * as vscode from 'vscode';
import * as path from 'path';
import { runCherenkovCommand, autoDetectSpec } from '../api/CherenkovClient';

export async function runValidate(
  outputChannel: vscode.OutputChannel,
  specPath?: string
): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;
  const config = vscode.workspace.getConfiguration('cherenkov');
  const targetUrl = config.get<string>('targetUrl', 'http://localhost:8000');
  const workers = config.get<number>('workers', 1);

  // Resolve spec path
  let spec = specPath ?? config.get<string>('specPath', '');
  if (!spec && config.get<boolean>('autoDetectSpec', true)) {
    spec = autoDetectSpec(root) ?? '';
  }

  outputChannel.show(true);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Cherenkov: Running conformance tests…',
      cancellable: true,
    },
    async (_progress, token) => {
      const args = ['validate', '--target', targetUrl, '--workers', String(workers), '--format', 'text'];
      if (spec) {
        args.push('--spec', spec);
      }

      const result = await runCherenkovCommand(args, outputChannel, root, token);

      if (token.isCancellationRequested) {
        return;
      }

      if (result.exitCode === 0) {
        vscode.window.showInformationMessage('Cherenkov: All conformance tests passed ✓');
      } else {
        vscode.window.showWarningMessage(
          'Cherenkov: Conformance violations detected — see output panel for details.',
          'Show Output'
        ).then(action => {
          if (action === 'Show Output') {
            outputChannel.show(true);
          }
        });
      }
    }
  );
}

export async function runValidateFile(
  uri: vscode.Uri,
  outputChannel: vscode.OutputChannel
): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;
  const relPath = path.relative(root, uri.fsPath);
  await runValidate(outputChannel, relPath);
}
