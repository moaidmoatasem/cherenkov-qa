import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Automated Verification for Problems panel', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        assert.ok(workspaceFolders, "Workspace folder should be open");
        
        const specUri = vscode.Uri.file(path.join(workspaceFolders[0].uri.fsPath, 'mock-spec.yaml'));
        const doc = await vscode.workspace.openTextDocument(specUri);
        await vscode.window.showTextDocument(doc);
        
        // Give the extension a moment to activate on document open
        await new Promise(r => setTimeout(r, 2000));
        
        // Trigger validation
        await vscode.commands.executeCommand('cherenkov.validate');
        
        // Give it time to run subprocess and parse
        await new Promise(r => setTimeout(r, 2000));
        
        // Check diagnostics
        const diagnostics = vscode.languages.getDiagnostics(specUri);
        assert.strictEqual(diagnostics.length, 1, "Should have 1 violation");
        
        const diagnostic = diagnostics[0];
        assert.strictEqual(diagnostic.message, "[CHERENKOV] POST /payments: Missing field 'amount'");
        assert.strictEqual(diagnostic.severity, vscode.DiagnosticSeverity.Warning);
        assert.strictEqual(diagnostic.source, 'CHERENKOV QA');
    }).timeout(15000);
});
