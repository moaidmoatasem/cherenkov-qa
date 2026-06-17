"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const client_1 = require("./backend/client");
const conformance_1 = require("./features/conformance");
const codeLens_1 = require("./features/codeLens");
const decorations_1 = require("./features/decorations");
function activate(context) {
    const client = new client_1.CherenkovClient();
    const diagnosticsCollection = vscode.languages.createDiagnosticCollection('cherenkov');
    const diagnosticsProvider = new conformance_1.ConformanceDiagnosticsProvider(diagnosticsCollection);
    const decorationProvider = new decorations_1.ConformanceDecorationProvider(context);
    const codeLensProvider = new codeLens_1.ConformanceCodeLensProvider();
    // Register Code Lens provider for OpenAPI files
    const codeLensDisposable = vscode.languages.registerCodeLensProvider([{ pattern: '**/*.yaml' }, { pattern: '**/*.yml' }, { pattern: '**/*.json' }], codeLensProvider);
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
                }
                else {
                    vscode.window.showWarningMessage(`⚠️ CHERENKOV: ${result.violations.length} conformance violation(s) found. See Problems panel.`, 'Open Problems').then(sel => {
                        if (sel === 'Open Problems') {
                            vscode.commands.executeCommand('workbench.action.problems.focus');
                        }
                    });
                }
            }
            catch (err) {
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
            }
            catch (err) {
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
        }
        catch (err) {
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
    context.subscriptions.push(diagnosticsCollection, codeLensDisposable, validateCmd, generateCmd, doctorCmd, clearCmd, onSaveDisposable);
}
function isOpenApiFile(doc) {
    const text = doc.getText(new vscode.Range(0, 0, 30, 0));
    return (text.includes('openapi') ||
        text.includes('swagger') ||
        text.includes('info:') ||
        text.includes('"info"'));
}
function deactivate() { }
//# sourceMappingURL=extension.js.map