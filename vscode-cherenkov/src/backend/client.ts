import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import { Violation, parseSarif } from './sarif';

// Re-export for consumers who import from client
export { Violation, parseSarif } from './sarif';

export interface ValidationResult {
    passed: boolean;
    violations: Violation[];
    raw?: string;
}

/**
 * CherenkovClient: wraps the CHERENKOV CLI / Python script.
 * All communication is via spawning a subprocess — no network required.
 */
export class CherenkovClient {
    private get config() {
        return vscode.workspace.getConfiguration('cherenkov');
    }

    private get pythonPath(): string {
        return this.config.get<string>('pythonPath', 'python');
    }

    private get targetUrl(): string {
        return this.config.get<string>('targetUrl', 'http://localhost:8080');
    }

    /**
     * Resolve the cherenkov.py script relative to a workspace folder,
     * falling back to the system `cherenkov` CLI command.
     */
    private resolveCli(specFile: string): { cmd: string; args: string[] } {
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
    public async validateSpec(specFile: string): Promise<ValidationResult> {
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
            proc.stdout.on('data', (d: Buffer) => { stdout += d.toString(); });
            proc.stderr.on('data', (d: Buffer) => { stderr += d.toString(); });

            proc.on('close', () => {
                const violations = parseSarif(stdout);
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
    public async generateTests(specFile: string): Promise<string> {
        return new Promise((resolve, reject) => {
            const { cmd, args } = this.resolveCli(specFile);
            const fullArgs = [...args, 'generate', '--spec', specFile];

            let stdout = '';
            let stderr = '';

            const proc = cp.spawn(cmd, fullArgs, { cwd: path.dirname(specFile) });
            proc.stdout.on('data', (d: Buffer) => { stdout += d.toString(); });
            proc.stderr.on('data', (d: Buffer) => { stderr += d.toString(); });
            proc.on('close', (code) => {
                if (code === 0) { resolve(stdout); }
                else { reject(new Error(stderr || stdout || `Exit code ${code}`)); }
            });
            proc.on('error', (err) => reject(err));
        });
    }

    /**
     * Run `cherenkov doctor` and return the output string.
     */
    public async doctor(workspaceRoot?: string): Promise<string> {
        return new Promise((resolve, reject) => {
            const cwd = workspaceRoot || process.cwd();
            const pyScript = path.join(cwd, 'cherenkov.py');
            const proc = cp.spawn(this.pythonPath, [pyScript, 'doctor'], { cwd });

            let out = '';
            proc.stdout.on('data', (d: Buffer) => { out += d.toString(); });
            proc.stderr.on('data', (d: Buffer) => { out += d.toString(); });
            proc.on('close', () => resolve(out));
            proc.on('error', (err) => reject(err));
        });
    }
}
