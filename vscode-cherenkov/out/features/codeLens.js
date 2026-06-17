"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConformanceCodeLensProvider = void 0;
const vscode = require("vscode");
class ConformanceCodeLensProvider {
    constructor() {
        this._onDidChangeCodeLenses = new vscode.EventEmitter();
        this.onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
    }
    provideCodeLenses(document, _token) {
        const lenses = [];
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
    refresh() {
        this._onDidChangeCodeLenses.fire();
    }
}
exports.ConformanceCodeLensProvider = ConformanceCodeLensProvider;
//# sourceMappingURL=codeLens.js.map