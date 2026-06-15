#!/usr/bin/env node
"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

function log(msg) {
  console.log(`[cherenkov-init] ${msg}`);
}

function error(msg) {
  console.error(`[cherenkov-init] ERROR: ${msg}`);
}

function run(cmd) {
  try {
    return execSync(cmd, { encoding: "utf-8", stdio: "pipe" }).trim();
  } catch {
    return null;
  }
}

function detectPython() {
  const commands = ["python3", "python"];
  for (const cmd of commands) {
    const version = run(`${cmd} --version`);
    if (version) {
      const match = version.match(/(\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major > 3 || (major === 3 && minor >= 10)) {
          return cmd;
        }
      }
    }
  }
  return null;
}

function detectPip(pythonCmd) {
  const pipCommands = [`${pythonCmd} -m pip`, "pip3", "pip"];
  for (const cmd of pipCommands) {
    const result = run(`${cmd} --version`);
    if (result) {
      return cmd;
    }
  }
  return null;
}

const DEFAULT_CONFIG = `# cherenkov.yaml - Default CHERENKOV QA Configuration
# See https://github.com/moaidmoatasem/cherenkov-qa for full options.

conformance:
  spec_path: null
  base_url: null
  timeout: 30

reporting:
  format: markdown
  output_dir: .cherenkov/reports

jira:
  enabled: false
  project_key: QA
`;

function main() {
  log("CHERENKOV QA — Bootstrap Init");
  log("============================");

  const pythonCmd = detectPython();
  if (!pythonCmd) {
    error("Python 3.10+ is required but was not found.");
    error("Install Python from https://www.python.org/downloads/");
    process.exit(1);
  }
  log(`Found Python: ${pythonCmd} (${run(`${pythonCmd} --version`)})`);

  const pipCmd = detectPip(pythonCmd);
  if (!pipCmd) {
    error("pip is required but was not found.");
    error("Install pip: https://pip.pypa.io/en/stable/installation/");
    process.exit(1);
  }
  log(`Found pip: ${pipCmd}`);

  log("Installing cherenkov...");
  try {
    execSync(`${pipCmd} install cherenkov`, { encoding: "utf-8", stdio: "inherit" });
    log("cherenkov installed successfully.");
  } catch (err) {
    error(`Failed to install cherenkov: ${err.message}`);
    process.exit(1);
  }

  const cwd = process.cwd();
  const configDir = path.join(cwd, ".cherenkov");
  const configPath = path.join(configDir, "cherenkov.yaml");

  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
    log(`Created config directory: ${configDir}`);
  }

  if (!fs.existsSync(configPath)) {
    fs.writeFileSync(configPath, DEFAULT_CONFIG, "utf-8");
    log(`Created default config: ${configPath}`);
  } else {
    log(`Config already exists: ${configPath} (skipped)`);
  }

  log("");
  log("Init complete!");
  log("");
  log("Next steps:");
  log("  1. Edit .cherenkov/cherenkov.yaml with your spec path and base URL");
  log("  2. Run: cherenkov doctor          # verify setup");
  log("  3. Run: cherenkov run             # start testing");
  log("");
}

main();
