import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface ConformanceReport {
  passed: number;
  failed: number;
  driftCount: number;
  findings: DriftFinding[];
  timestamp: string;
}

export interface DriftFinding {
  endpoint: string;
  method: string;
  severity: 'high' | 'medium' | 'low';
  expected: string;
  actual: string;
  scenario: string;
}

export interface HealthStatus {
  online: boolean;
  demoMode: boolean;
  genModel?: string;
}

function getPythonPath(): string {
  return vscode.workspace.getConfiguration('cherenkov').get<string>('pythonPath', 'python3');
}

function getCherenkovEntry(workspaceRoot: string): string {
  const local = path.join(workspaceRoot, 'cherenkov.py');
  if (fs.existsSync(local)) {
    return local;
  }
  // Fallback: installed module
  return '-m cherenkov';
}

export async function runCherenkovCommand(
  args: string[],
  outputChannel: vscode.OutputChannel,
  workspaceRoot: string,
  token?: vscode.CancellationToken
): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  const python = getPythonPath();
  const entry = getCherenkovEntry(workspaceRoot);
  const isModule = entry.startsWith('-m');
  const cmdArgs = isModule ? ['-m', 'cherenkov', ...args] : [entry, ...args];

  outputChannel.appendLine(`\n$ ${python} ${cmdArgs.join(' ')}`);
  outputChannel.appendLine('─'.repeat(60));

  return new Promise((resolve) => {
    const proc = cp.spawn(python, cmdArgs, {
      cwd: workspaceRoot,
      env: { ...process.env, PYTHONPATH: workspaceRoot },
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data: Buffer) => {
      const text = data.toString();
      stdout += text;
      outputChannel.append(text);
    });

    proc.stderr.on('data', (data: Buffer) => {
      const text = data.toString();
      stderr += text;
      outputChannel.append(text);
    });

    if (token) {
      token.onCancellationRequested(() => {
        proc.kill();
        outputChannel.appendLine('\n[Cancelled]');
      });
    }

    proc.on('close', (code) => {
      resolve({ exitCode: code ?? 1, stdout, stderr });
    });

    proc.on('error', (err) => {
      outputChannel.appendLine(`\n[Error] ${err.message}`);
      resolve({ exitCode: 1, stdout, stderr: err.message });
    });
  });
}

export async function fetchHealth(baseUrl: string): Promise<HealthStatus> {
  try {
    const res = await fetch(`${baseUrl}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      return { online: false, demoMode: false };
    }
    const data = await res.json() as { status?: string; demo_mode?: boolean; gen_model?: string };
    return {
      online: data.status === 'online',
      demoMode: Boolean(data.demo_mode),
      genModel: data.gen_model,
    };
  } catch {
    return { online: false, demoMode: false };
  }
}

export async function fetchLastReport(baseUrl: string): Promise<ConformanceReport | null> {
  try {
    const res = await fetch(`${baseUrl}/api/v1/report`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      return null;
    }
    return await res.json() as ConformanceReport;
  } catch {
    return null;
  }
}

export function autoDetectSpec(workspaceRoot: string): string | undefined {
  const candidates = [
    'openapi.yaml', 'openapi.json', 'openapi.yml',
    'api/openapi.yaml', 'api/openapi.json',
    'stub/openapi.yaml', 'spec/openapi.yaml',
    'docs/openapi.yaml', 'swagger.yaml', 'swagger.json',
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(workspaceRoot, c))) {
      return c;
    }
  }
  return undefined;
}
