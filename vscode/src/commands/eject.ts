import * as vscode from 'vscode';
import * as path from 'path';
import { runCherenkovCommand } from '../api/CherenkovClient';

export async function runEject(outputChannel: vscode.OutputChannel): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders?.length) {
    vscode.window.showErrorMessage('Cherenkov: No workspace folder open.');
    return;
  }
  const root = workspaceFolders[0].uri.fsPath;

  const outputPath = await vscode.window.showInputBox({
    prompt: 'Output directory for standalone Playwright suite',
    placeHolder: './playwright-suite',
    value: './playwright-suite',
  });

  if (!outputPath) {
    return;
  }

  outputChannel.show(true);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Cherenkov: Ejecting to vanilla Playwright…',
      cancellable: false,
    },
    async () => {
      const absOutput = path.resolve(root, outputPath);
      const result = await runCherenkovCommand(
        ['eject', '--output', absOutput],
        outputChannel,
        root
      );

      if (result.exitCode === 0) {
        const open = 'Open Folder';
        const action = await vscode.window.showInformationMessage(
          `Cherenkov: Ejected to ${outputPath} — runs with npx playwright test, zero CHERENKOV dependency.`,
          open
        );
        if (action === open) {
          const uri = vscode.Uri.file(absOutput);
          await vscode.commands.executeCommand('vscode.openFolder', uri, { forceNewWindow: true });
        }
      } else {
        vscode.window.showErrorMessage('Cherenkov: Eject failed — see output panel for details.');
      }
    }
  );
}
