"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConformanceDiagnosticsProvider = void 0;
const vscode = require("vscode");
class ConformanceDiagnosticsProvider {
    constructor(collection) {
        this.collection = collection;
    }
    update(document, violations) {
        this.collection.clear();
        if (violations.length === 0) {
            return;
        }
        const diagnostics = violations.map((v) => {
            const line = this.findEndpointLine(document, v.endpoint, v.method);
            const range = new vscode.Range(line, 0, line, 0);
            const diag = new vscode.Diagnostic(range, `[CHERENKOV] ${v.method} ${v.endpoint}: ${v.error}`, vscode.DiagnosticSeverity.Warning);
            diag.source = 'CHERENKOV QA';
            diag.code = 'conformance-drift';
            return diag;
        });
        this.collection.set(document.uri, diagnostics);
    }
    clear() {
        this.collection.clear();
    }
    findEndpointLine(document, endpoint, _method) {
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
exports.ConformanceDiagnosticsProvider = ConformanceDiagnosticsProvider;
//# sourceMappingURL=conformance.js.map