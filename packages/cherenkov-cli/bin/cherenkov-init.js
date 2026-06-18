#!/usr/bin/env node
/**
 * cherenkov-cli — Zero-install quickstart for CHERENKOV
 *
 * Usage:
 *   npx cherenkov-cli init
 *   npx cherenkov-cli validate --spec openapi.yaml --target http://localhost:3000
 *
 * This wrapper:
 *   1. Verifies Python >= 3.10 is available
 *   2. Installs cherenkov-qa via pip (idempotent)
 *   3. Delegates to `cherenkov` CLI with all args forwarded
 */

'use strict';

const { execSync, spawnSync } = require('child_process');
const path = require('path');

const MIN_PYTHON_MAJOR = 3;
const MIN_PYTHON_MINOR = 10;
const PACKAGE_NAME = 'cherenkov-qa';

function findPython() {
  const candidates = ['python3', 'python'];
  for (const cmd of candidates) {
    try {
      const result = execSync(`${cmd} --version 2>&1`, { encoding: 'utf8', stdio: 'pipe' });
      const match = result.match(/Python (\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major > MIN_PYTHON_MAJOR || (major === MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR)) {
          return cmd;
        }
      }
    } catch (_) { /* not found */ }
  }
  return null;
}

function installCherenkov(python) {
  process.stderr.write(`\n⚡ Installing ${PACKAGE_NAME} via pip...\n`);
  const result = spawnSync(python, ['-m', 'pip', 'install', PACKAGE_NAME, '--quiet', '--upgrade'], {
    stdio: 'inherit',
  });
  if (result.status !== 0) {
    process.stderr.write(`\n❌ Failed to install ${PACKAGE_NAME}. Try: pip install ${PACKAGE_NAME}\n`);
    process.exit(1);
  }
}

function isCherenkovInstalled(python) {
  try {
    const result = execSync(`${python} -m pip show ${PACKAGE_NAME} 2>&1`, { encoding: 'utf8', stdio: 'pipe' });
    return result.includes('Name:');
  } catch (_) {
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);

  // --help or no args: show usage
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
CHERENKOV CLI — AI-native API conformance test generator

Usage:
  npx cherenkov-cli <command> [options]

Commands:
  init                      Interactive project setup
  generate --spec <file>    Generate Playwright tests from OpenAPI spec
  validate --spec <file> --target <url>
                            Run conformance tests against live server
  eject --output <dir>      Export standalone Playwright tests (zero lock-in)
  doctor                    Check LLM and system health
  heal                      Review healing suggestions (suggest-only, never auto-edits)

Options:
  --help, -h    Show this help

Examples:
  npx cherenkov-cli init
  npx cherenkov-cli validate --spec openapi.yaml --target http://localhost:3000
  npx cherenkov-cli eject --output ./tests

Documentation:
  https://github.com/moaidmoatasem/cherenkov-qa/blob/main/docs/GETTING_STARTED.md
`);
    process.exit(0);
  }

  // Find Python
  const python = findPython();
  if (!python) {
    console.error(`
❌ Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} is required but not found.

Install Python from https://python.org/downloads/ then re-run:
  npx cherenkov-cli ${args.join(' ')}
`);
    process.exit(1);
  }

  // Install cherenkov-qa if not present
  if (!isCherenkovInstalled(python)) {
    installCherenkov(python);
  }

  // Delegate to cherenkov CLI
  const result = spawnSync(python, ['-m', 'cherenkov.cli.core', ...args], {
    stdio: 'inherit',
    env: { ...process.env },
  });

  // Fall back to direct `cherenkov` command if module invocation fails
  if (result.status !== 0 && result.error) {
    const fallback = spawnSync('cherenkov', args, { stdio: 'inherit' });
    process.exit(fallback.status ?? 1);
  }

  process.exit(result.status ?? 0);
}

main();
