import * as vscode from 'vscode';

export class ConformanceCodeLensProvider implements vscode.CodeLensProvider {
    private readonly _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

    public provideCodeLenses(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken
    ): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];
        const lines = document.getText().split('\n');

        const pathRegex = /^\s+(\/[a-zA-Z0-9_\-\/{}]+)\s*:/;

        for (let i = 0; i < lines.length; i++) {
            const match = pathRegex.exec(lines[i]);
            if (match) {
                const range = new vscode.Range(i, 0, i, lines[i].length);

                lenses.push(new vscode.CodeLens(range, {
                    title: '▶ Validate Conformance',
                    command: 'cherenkov.validate',
                    tooltip: 'Run CHERENKOV conformance validation on this spec',
                }));

                lenses.push(new vscode.CodeLens(range, {
                    title: '⚙ Generate Tests',
                    command: 'cherenkov.generateTests',
                    tooltip: 'Generate conformance tests from this spec',
                }));
            }
        }

        return lenses;
    }

    public refresh(): void {
        this._onDidChangeCodeLenses.fire();
    }
}
