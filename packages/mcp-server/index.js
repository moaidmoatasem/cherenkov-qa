#!/usr/bin/env node
'use strict';

/**
 * @cherenkov-qa/mcp-server
 *
 * Thin Node.js shim that spawns the CHERENKOV Python MCP server over stdio.
 * The Python package performs the actual JSON-RPC handling; this wrapper just
 * wires stdin/stdout and ensures a clean shutdown.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

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

function findCherenkovEntry() {
  // When running inside the published package, the repo root is two levels up.
  const packagedRoot = path.resolve(__dirname, '../..');
  const cherenkovPy = path.join(packagedRoot, 'cherenkov.py');
  if (fs.existsSync(cherenkovPy)) return cherenkovPy;

  // Fall back to installed Python module.
  return null;
}

const python = findPython();
if (!python) {
  process.stderr.write('CHERENKOV MCP server requires Python 3.10 or later.\n');
  process.exit(1);
}

const entry = findCherenkovEntry();
const args = entry ? [entry, 'mcp', 'serve'] : ['-m', 'cherenkov', 'mcp', 'serve'];

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
