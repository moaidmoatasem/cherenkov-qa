#!/usr/bin/env node
/**
 * npx cherenkov — thin Node.js shim that delegates to the Python CLI.
 *
 * Checks Python 3.10+ is available, then forwards all arguments to
 * `python3 cherenkov.py` in the current working directory (or falls back
 * to the globally installed `cherenkov` entry-point if the local copy isn't
 * found).  The shim exits with the same code as the Python process.
 */

'use strict';

const { execFileSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

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

// Prefer the local cherenkov.py (works from a git clone / extracted archive)
const localEntry = path.join(process.cwd(), 'cherenkov.py');
const args = process.argv.slice(2);

let proc;
if (fs.existsSync(localEntry)) {
  proc = spawnSync(python, [localEntry, ...args], { stdio: 'inherit' });
} else {
  // Fall back to installed entry-point (pip install cherenkov-qa)
  proc = spawnSync(python, ['-m', 'cherenkov', ...args], { stdio: 'inherit' });
}

process.exit(proc.status ?? 1);
