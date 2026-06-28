import * as vscode from 'vscode';
import { runValidate, runValidateFile } from './commands/validate';
import { runGenerate } from './commands/generate';
import { runEject } from './commands/eject';
import { runDoctor, runInit } from './commands/doctor';
import { ConformanceTreeProvider } from './providers/TreeDataProvider';
import { CherenkovCodeLensProvider } from './providers/CodeLensProvider';
import { CherenkovDiagnosticsProvider } from './providers/DiagnosticsProvider';
import { CherenkovHoverProvider } from './providers/HoverProvider';
import { CherenkovQuickFixProvider } from './providers/QuickFixProvider';
import { CherenkovGutterProvider } from './providers/GutterProvider';
import { CherenkovTestExplorer } from './providers/TestExplorer';
import { ConformancePanel } from './views/ConformancePanel';
import { fetchHealth, fetchLastReport } from './api/CherenkovClient';

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('Cherenkov QA');
  const config = vscode.workspace.getConfiguration('cherenkov');
  const baseUrl = config.get<string>('targetUrl', 'http://localhost:8000');

  // Sidebar tree view
  const treeProvider = new ConformanceTreeProvider(baseUrl);
  const treeView = vscode.window.createTreeView('cherenkovExplorer', {
    treeDataProvider: treeProvider,
    showCollapseAll: true,
  });

  // Code lens for OpenAPI files
  const codeLensProvider = new CherenkovCodeLensProvider();
  const codeLensDisposable = vscode.languages.registerCodeLensProvider(
    [{ language: 'yaml' }, { language: 'json' }],
    codeLensProvider
  );

  // Diagnostics, hover, and quick fix providers
  const diagnosticsProvider = new CherenkovDiagnosticsProvider();
  const hoverProvider = new CherenkovHoverProvider();
  const quickFixProvider = new CherenkovQuickFixProvider();

  const hoverDisposable = vscode.languages.registerHoverProvider(
    [{ language: 'yaml' }, { language: 'json' }],
    hoverProvider
  );

  const quickFixDisposable = vscode.languages.registerCodeActionsProvider(
    [{ language: 'yaml' }, { language: 'json' }],
    quickFixProvider,
    { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
  );

  const gutterProvider = new CherenkovGutterProvider();
  const testExplorer = new CherenkovTestExplorer(outputChannel, baseUrl);

  vscode.window.onDidChangeActiveTextEditor(editor => {
    if (editor) {
      const report = treeProvider.getReport();
      gutterProvider.updateDecorations(editor, report);
    }
  });

  vscode.workspace.onDidChangeTextDocument(e => {
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document === e.document) {
      const report = treeProvider.getReport();
      gutterProvider.updateDecorations(editor, report);
    }
  });

  vscode.workspace.onDidSaveTextDocument(async doc => {
    const ext = doc.uri.fsPath.toLowerCase();
    if (ext.endsWith('.yaml') || ext.endsWith('.yml') || ext.endsWith('.json')) {
      if (doc.getText().includes('openapi:') || doc.getText().includes('"openapi"')) {
        await runValidateFile(doc.uri, outputChannel);
        await treeProvider.refresh();
        void pollHealth();
      }
    }
  });

  // Status bar item
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.text = '$(beaker) Cherenkov';
  statusBar.tooltip = 'Cherenkov QA — click to check environment health';
  statusBar.command = 'cherenkov.doctor';
  statusBar.show();

  // Poll backend health and update status bar
  async function pollHealth(): Promise<void> {
    const currentUrl = vscode.workspace.getConfiguration('cherenkov').get<string>('targetUrl', 'http://localhost:8000');
    treeProvider.updateBaseUrl(currentUrl);
    const health = await fetchHealth(currentUrl);
    if (health.online) {
      statusBar.text = `$(pass) Cherenkov ${health.demoMode ? '(demo)' : '(live)'}`;
      statusBar.backgroundColor = undefined;
      const report = await fetchLastReport(currentUrl);
      treeProvider.setReport(report);
      codeLensProvider.setReport(report);
      hoverProvider.setReport(report);
      testExplorer.updateBaseUrl(currentUrl);

      vscode.workspace.textDocuments.forEach(doc => {
        const ext = doc.uri.fsPath.toLowerCase();
        if (ext.endsWith('.yaml') || ext.endsWith('.yml') || ext.endsWith('.json')) {
          diagnosticsProvider.updateDiagnostics(doc, report);
        }
      });
      vscode.window.visibleTextEditors.forEach(editor => {
        gutterProvider.updateDecorations(editor, report);
      });
    } else {
      statusBar.text = '$(warning) Cherenkov (offline)';
    }
  }

  void pollHealth();
  const healthPoller = setInterval(() => void pollHealth(), 30_000);

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand('cherenkov.validate', async () => {
      await runValidate(outputChannel);
      await treeProvider.refresh();
      const report = await fetchLastReport(baseUrl);
      codeLensProvider.setReport(report);
    }),

    vscode.commands.registerCommand('cherenkov.validateFile', async (uri: vscode.Uri) => {
      await runValidateFile(uri, outputChannel);
      await treeProvider.refresh();
    }),

    vscode.commands.registerCommand('cherenkov.generate', async (uri?: vscode.Uri) => {
      await runGenerate(outputChannel, uri);
      await treeProvider.refresh();
    }),

    vscode.commands.registerCommand('cherenkov.eject', () => runEject(outputChannel)),

    vscode.commands.registerCommand('cherenkov.doctor', () => runDoctor(outputChannel)),

    vscode.commands.registerCommand('cherenkov.init', () => runInit(outputChannel)),

    vscode.commands.registerCommand('cherenkov.openDashboard', () => {
      const dashUrl = vscode.workspace.getConfiguration('cherenkov').get<string>('targetUrl', 'http://localhost:8000');
      void vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    }),

    vscode.commands.registerCommand('cherenkov.refreshTree', async () => {
      await treeProvider.refresh();
    }),

    vscode.commands.registerCommand('cherenkov.generateAssertion', async () => {
      await runValidate(outputChannel);
      await treeProvider.refresh();
      const report = await fetchLastReport(baseUrl);
      codeLensProvider.setReport(report);
      hoverProvider.setReport(report);
    }),

    vscode.commands.registerCommand('cherenkov.viewDrift', () => {
      ConformancePanel.createOrShow(context.extensionUri, treeProvider.getReport());
    }),

    // Config change listener
    vscode.workspace.onDidChangeConfiguration(e => {
      if (e.affectsConfiguration('cherenkov')) {
        void pollHealth();
      }
    }),

    outputChannel,
    treeView,
    codeLensDisposable,
    hoverDisposable,
    quickFixDisposable,
    diagnosticsProvider,
    gutterProvider,
    testExplorer,
    statusBar,
    { dispose: () => clearInterval(healthPoller) }
  );
}

export function deactivate(): void {
  // cleanup handled by disposables
}
