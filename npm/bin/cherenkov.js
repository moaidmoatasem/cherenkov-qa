#!/usr/bin/env node

/**
 * cherenkov-qa NPM Wrapper
 * Bootstraps the Python CLI environment and forwards commands.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function runCommand(cmd, options = {}) {
    try {
        return execSync(cmd, { stdio: 'inherit', ...options });
    } catch (err) {
        process.exit(err.status || 1);
    }
}

function checkPython() {
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return 'python3';
    } catch (e) {
        try {
            execSync('python --version', { stdio: 'ignore' });
            return 'python';
        } catch (e2) {
            console.error('\x1b[31m[CHERENKOV] Error: Python 3.10+ is required but not found.\x1b[0m');
            console.error('Please install Python from https://python.org and try again.');
            process.exit(1);
        }
    }
}

function main() {
    const args = process.argv.slice(2);
    const pythonExe = checkPython();
    
    // In a real published package, this would install via pip if not found:
    // runCommand(`${pythonExe} -m pip install cherenkov-qa`);
    // Since this is the local repository wrapper, we assume it's running locally or will just execute the local module.
    
    // Determine where to run it
    const cherenkovMod = 'cherenkov'; // Assuming it's installed or in PYTHONPATH
    
    // Run the Python CLI and pass the arguments along
    const command = `${pythonExe} -m ${cherenkovMod} ${args.join(' ')}`;
    
    // Set PYTHONPATH so it can find the local 'cherenkov' package if run from the repo root
    const env = { ...process.env };
    if (!env.PYTHONPATH) {
        env.PYTHONPATH = path.resolve(__dirname, '../../');
    } else {
        env.PYTHONPATH = `${path.resolve(__dirname, '../../')}:${env.PYTHONPATH}`;
    }
    
    runCommand(command, { env });
}

main();
