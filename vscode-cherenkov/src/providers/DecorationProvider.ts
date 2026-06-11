import * as vscode from 'vscode';
import { Violation } from '../backend/client';

/**
 * ConformanceDecorationProvider
 *
 * Renders gutter icons and line decorations:
 *  🟢 Green dot — endpoint line, all checks passing
 *  🔴 Red dot  — endpoint line, drift violation detected
 */
export class ConformanceDecorationProvider {
    private readonly failType: vscode.TextEditorDecorationType;
    private readonly passType: vscode.TextEditorDecorationType;

    constructor(context: vscode.ExtensionContext) {
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

    public update(editor: vscode.TextEditor, violations: Violation[]): void {
        const document = editor.document;
        const text = document.getText();
        const lines = text.split('\n');
        const pathRegex = /^\s+(\/[a-zA-Z0-9_\-\/{}]+)\s*:/;

        const failingEndpoints = new Set(violations.map(v => v.endpoint));
        const failRanges: vscode.DecorationOptions[] = [];
        const passRanges: vscode.DecorationOptions[] = [];

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
                } else {
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

    public clear(): void {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            editor.setDecorations(this.failType, []);
            editor.setDecorations(this.passType, []);
        }
    }
}
