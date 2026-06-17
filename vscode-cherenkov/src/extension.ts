import * as vscode from 'vscode';
import { CherenkovClient, Violation } from './backend/client';
import { ConformanceDiagnosticsProvider } from './features/conformance';
import { ConformanceCodeLensProvider } from './features/codeLens';
import { ConformanceDecorationProvider } from './features/decorations';

export function activate(context: vscode.ExtensionContext) {
    const client = new CherenkovClient();
    const diagnosticsCollection = vscode.languages.createDiagnosticCollection('cherenkov');
    const diagnosticsProvider = new ConformanceDiagnosticsProvider(diagnosticsCollection);
    const decorationProvider = new ConformanceDecorationProvider(context);
    const codeLensProvider = new ConformanceCodeLensProvider();

    // Register Code Lens provider for OpenAPI files
    const codeLensDisposable = vscode.languages.registerCodeLensProvider(
        [{ pattern: '**/*.yaml' }, { pattern: '**/*.yml' }, { pattern: '**/*.json' }],
        codeLensProvider
    );

    // ── Commands ──────────────────────────────────────────────────────────────

    const validateCmd = vscode.commands.registerCommand('cherenkov.validate', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('CHERENKOV: No active file to validate.');
            return;
        }

        const specFile = editor.document.uri.fsPath;
        if (!isOpenApiFile(editor.document)) {
            vscode.window.showWarningMessage('CHERENKOV: Active file does not appear to be an OpenAPI spec.');
            return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'CHERENKOV: Running conformance validation…',
            cancellable: false,
        }, async () => {
            try {
                const result = await client.validateSpec(specFile);
                diagnosticsProvider.update(editor.document, result.violations);
                decorationProvider.update(editor, result.violations);

                if (result.passed) {
                    vscode.window.showInformationMessage('✅ CHERENKOV: All conformance checks passed!');
                } else {
                    vscode.window.showWarningMessage(
                        `⚠️ CHERENKOV: ${result.violations.length} conformance violation(s) found. See Problems panel.`,
                        'Open Problems'
                    ).then(sel => {
                        if (sel === 'Open Problems') {
                            vscode.commands.executeCommand('workbench.action.problems.focus');
                        }
                    });
                }
            } catch (err: any) {
                vscode.window.showErrorMessage(`CHERENKOV validation failed: ${err.message}`);
            }
        });
    });

    const generateCmd = vscode.commands.registerCommand('cherenkov.generateTests', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || !isOpenApiFile(editor.document)) {
            vscode.window.showWarningMessage('CHERENKOV: Open an OpenAPI spec file first.');
            return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'CHERENKOV: Generating conformance tests…',
            cancellable: false,
        }, async () => {
            try {
                const output = await client.generateTests(editor.document.uri.fsPath);
                vscode.window.showInformationMessage(`✅ CHERENKOV: Tests generated successfully!`);
                // Auto-trigger validation after generation
                vscode.commands.executeCommand('cherenkov.validate');
            } catch (err: any) {
                vscode.window.showErrorMessage(`CHERENKOV generation failed: ${err.message}`);
            }
        });
    });

    const doctorCmd = vscode.commands.registerCommand('cherenkov.doctor', async () => {
        const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        const panel = vscode.window.createOutputChannel('CHERENKOV Doctor');
        panel.show();
        panel.appendLine('Running CHERENKOV doctor…');

        try {
            const output = await client.doctor(wsFolder);
            panel.appendLine(output);
        } catch (err: any) {
            panel.appendLine(`Error: ${err.message}`);
        }
    });

    const clearCmd = vscode.commands.registerCommand('cherenkov.clearDiagnostics', () => {
        diagnosticsCollection.clear();
        decorationProvider.clear();
        vscode.window.showInformationMessage('CHERENKOV: Violations cleared.');
    });

    // Auto-validate on save for OpenAPI files
    const onSaveDisposable = vscode.workspace.onDidSaveTextDocument((doc) => {
        if (isOpenApiFile(doc)) {
            vscode.commands.executeCommand('cherenkov.validate');
        }
    });

    context.subscriptions.push(
        diagnosticsCollection,
        codeLensDisposable,
        validateCmd,
        generateCmd,
        doctorCmd,
        clearCmd,
        onSaveDisposable,
    );
}

function isOpenApiFile(doc: vscode.TextDocument): boolean {
    const text = doc.getText(new vscode.Range(0, 0, 30, 0));
    return (
        text.includes('openapi') ||
        text.includes('swagger') ||
        text.includes('info:') ||
        text.includes('"info"')
    );
}

export function deactivate() {}
