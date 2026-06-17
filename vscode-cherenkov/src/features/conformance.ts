import * as vscode from 'vscode';
import { Violation } from '../backend/client';

export class ConformanceDiagnosticsProvider {
    constructor(private readonly collection: vscode.DiagnosticCollection) {}

    public update(document: vscode.TextDocument, violations: Violation[]): void {
        this.collection.clear();

        if (violations.length === 0) {
            return;
        }

        const diagnostics: vscode.Diagnostic[] = violations.map((v) => {
            const line = this.findEndpointLine(document, v.endpoint, v.method);
            const range = new vscode.Range(line, 0, line, 0);

            const diag = new vscode.Diagnostic(
                range,
                `[CHERENKOV] ${v.method} ${v.endpoint}: ${v.error}`,
                vscode.DiagnosticSeverity.Warning
            );
            diag.source = 'CHERENKOV QA';
            diag.code = 'conformance-drift';
            return diag;
        });

        this.collection.set(document.uri, diagnostics);
    }

    public clear(): void {
        this.collection.clear();
    }

    private findEndpointLine(
        document: vscode.TextDocument,
        endpoint: string,
        _method: string
    ): number {
        const text = document.getText();
        const lines = text.split('\n');
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes(endpoint)) {
                return i;
            }
        }
        return 0;
    }
}
