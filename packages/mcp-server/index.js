#!/usr/bin/env node
'use strict';

/**
 * @cherenkov-qa/mcp-server
 *
 * Thin Node.js shim that spawns the CHERENKOV Python MCP server over stdio
 * via the canonical `python -m cherenkov mcp serve` entry point. The Python
 * package performs the actual JSON-RPC handling; this wrapper just wires
 * stdin/stdout and ensures a clean shutdown.
 */

const { spawn } = require('child_process');

function findPython() {
  for (const candidate of ['python3', 'python']) {
    try {
      const result = require('child_process').spawnSync(candidate, ['--version'], { encoding: 'utf8' });
      if (result.status !== 0 || result.error) continue;
      const match = (result.stdout || result.stderr || '').match(/Python (\d+)\.(\d+)/);
      if (match && (parseInt(match[1]) > 3 || (parseInt(match[1]) === 3 && parseInt(match[2]) >= 10))) {
        return candidate;
      }
    } catch { /* skip */ }
  }
  return null;
}

const python = findPython();
if (!python) {
  process.stderr.write('CHERENKOV MCP server requires Python 3.10 or later.\n');
  process.exit(1);
}

const args = ['-m', 'cherenkov', 'mcp', 'serve'];

const proc = spawn(python, args, {
  stdio: ['pipe', 'pipe', 'pipe'],
  cwd: process.cwd(),
});

process.stdin.pipe(proc.stdin);
proc.stdout.pipe(process.stdout);
proc.stderr.pipe(process.stderr);

proc.on('exit', (code) => {
  process.exit(code ?? 0);
});

process.on('SIGINT', () => {
  proc.kill('SIGINT');
});

process.on('SIGTERM', () => {
  proc.kill('SIGTERM');
});
