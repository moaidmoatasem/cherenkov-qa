#!/usr/bin/env node
/**
 * npx cherenkov — thin Node.js shim that delegates to the Python CLI.
 *
 * Checks Python 3.10+ is available, then forwards all arguments to
 * `python -m cherenkov` (the package entry point, resolved from the current
 * working directory or the installed distribution).  The shim exits with the
 * same code as the Python process.
 */

'use strict';

const { spawnSync } = require('child_process');

function findPython() {
  for (const candidate of ['python3', 'python']) {
    try {
      const result = spawnSync(candidate, ['--version'], { encoding: 'utf8' });
      if (result.status !== 0 || result.error) continue;
      // Parse "Python 3.X.Y"
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
  process.stderr.write(
    'cherenkov requires Python 3.10 or later.\n' +
    'Install from https://python.org or your system package manager.\n'
  );
  process.exit(1);
}

const args = process.argv.slice(2);
const proc = spawnSync(python, ['-m', 'cherenkov', ...args], { stdio: 'inherit' });

process.exit(proc.status ?? 1);
