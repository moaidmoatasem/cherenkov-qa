import * as vscode from 'vscode';
import { Violation } from '../backend/client';

/**
 * ConformanceDiagnosticsProvider
 *
 * Populates the VS Code Problems panel with CHERENKOV conformance violations.
 * Each violation maps to a Diagnostic on the line where the endpoint is
 * declared in the OpenAPI spec (or line 0 as fallback).
 */
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

    /**
     * Scan the document text to find the line number where the endpoint path
     * is declared. Falls back to line 0 if not found.
     */
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
