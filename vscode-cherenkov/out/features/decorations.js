"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConformanceDecorationProvider = void 0;
const vscode = require("vscode");
class ConformanceDecorationProvider {
    constructor(context) {
        this.failType = vscode.window.createTextEditorDecorationType({
            gutterIconPath: context.asAbsolutePath('images/gutter-fail.svg'),
            gutterIconSize: '70%',
            overviewRulerColor: new vscode.ThemeColor('editorWarning.foreground'),
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
        this.passType = vscode.window.createTextEditorDecorationType({
            gutterIconPath: context.asAbsolutePath('images/gutter-pass.svg'),
            gutterIconSize: '70%',
        });
        context.subscriptions.push(this.failType, this.passType);
    }
    update(editor, violations) {
        const document = editor.document;
        const lines = document.getText().split('\n');
        const pathRegex = /^\s+(\/[a-zA-Z0-9_\-\/{}]+)\s*:/;
        const failingEndpoints = new Set(violations.map(v => v.endpoint));
        const failRanges = [];
        const passRanges = [];
        for (let i = 0; i < lines.length; i++) {
            const match = pathRegex.exec(lines[i]);
            if (match) {
                const endpoint = match[1];
                const range = new vscode.Range(i, 0, i, 0);
                if (failingEndpoints.has(endpoint)) {
                    failRanges.push({
                        range,
                        hoverMessage: `⚠️ CHERENKOV: Conformance drift on ${endpoint}`,
                    });
                }
                else {
                    passRanges.push({
                        range,
                        hoverMessage: `✅ CHERENKOV: ${endpoint} passes conformance checks`,
                    });
                }
            }
        }
        editor.setDecorations(this.failType, failRanges);
        editor.setDecorations(this.passType, passRanges);
    }
    clear() {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            editor.setDecorations(this.failType, []);
            editor.setDecorations(this.passType, []);
        }
    }
}
exports.ConformanceDecorationProvider = ConformanceDecorationProvider;
//# sourceMappingURL=decorations.js.map