"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CherenkovClient = exports.parseSarif = void 0;
const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");
const sarif_1 = require("./sarif");
// Re-export for consumers who import from client
var sarif_2 = require("./sarif");
Object.defineProperty(exports, "parseSarif", { enumerable: true, get: function () { return sarif_2.parseSarif; } });
/**
 * CherenkovClient: wraps the CHERENKOV CLI / Python script.
 * All communication is via spawning a subprocess — no network required.
 */
class CherenkovClient {
    get config() {
        return vscode.workspace.getConfiguration('cherenkov');
    }
    get pythonPath() {
        return this.config.get('pythonPath', 'python');
    }
    get targetUrl() {
        return this.config.get('targetUrl', 'http://localhost:8080');
    }
    /**
     * Resolve the cherenkov.py script relative to a workspace folder,
     * falling back to the system `cherenkov` CLI command.
     */
    resolveCli(specFile) {
        const wsFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(specFile));
        if (wsFolder) {
            const pyScript = path.join(wsFolder.uri.fsPath, 'cherenkov.py');
            return { cmd: this.pythonPath, args: [pyScript] };
        }
        return { cmd: 'cherenkov', args: [] };
    }
    /**
     * Run `cherenkov validate --spec <file> --target <url> --output-format sarif`
     * and parse the SARIF JSON output into Violation objects.
     */
    async validateSpec(specFile) {
        return new Promise((resolve) => {
            const { cmd, args } = this.resolveCli(specFile);
            const fullArgs = [
                ...args,
                'validate',
                '--spec', specFile,
                '--target', this.targetUrl,
                '--output-format', 'sarif'
            ];
            let stdout = '';
            let stderr = '';
            const proc = cp.spawn(cmd, fullArgs, { cwd: path.dirname(specFile) });
            proc.stdout.on('data', (d) => { stdout += d.toString(); });
            proc.stderr.on('data', (d) => { stderr += d.toString(); });
            proc.on('close', () => {
                const violations = (0, sarif_1.parseSarif)(stdout);
                resolve({
                    passed: violations.length === 0,
                    violations,
                    raw: stdout || stderr
                });
            });
            proc.on('error', (err) => {
                resolve({
                    passed: false,
                    violations: [{
                            endpoint: 'CLI',
                            method: 'N/A',
                            error: `Failed to spawn CHERENKOV: ${err.message}`
                        }],
                    raw: err.message
                });
            });
        });
    }
    /**
     * Run `cherenkov generate --spec <file>` and return stdout.
     */
    async generateTests(specFile) {
        return new Promise((resolve, reject) => {
            const { cmd, args } = this.resolveCli(specFile);
            const fullArgs = [...args, 'generate', '--spec', specFile];
            let stdout = '';
            let stderr = '';
            const proc = cp.spawn(cmd, fullArgs, { cwd: path.dirname(specFile) });
            proc.stdout.on('data', (d) => { stdout += d.toString(); });
            proc.stderr.on('data', (d) => { stderr += d.toString(); });
            proc.on('close', (code) => {
                if (code === 0) {
                    resolve(stdout);
                }
                else {
                    reject(new Error(stderr || stdout || `Exit code ${code}`));
                }
            });
            proc.on('error', (err) => reject(err));
        });
    }
    /**
     * Run `cherenkov doctor` and return the output string.
     */
    async doctor(workspaceRoot) {
        return new Promise((resolve, reject) => {
            const cwd = workspaceRoot || process.cwd();
            const pyScript = path.join(cwd, 'cherenkov.py');
            const proc = cp.spawn(this.pythonPath, [pyScript, 'doctor'], { cwd });
            let out = '';
            proc.stdout.on('data', (d) => { out += d.toString(); });
            proc.stderr.on('data', (d) => { out += d.toString(); });
            proc.on('close', () => resolve(out));
            proc.on('error', (err) => reject(err));
        });
    }
}
exports.CherenkovClient = CherenkovClient;
//# sourceMappingURL=client.js.map