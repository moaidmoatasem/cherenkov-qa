#!/usr/bin/env node

const { execSync } = require("child_process");

function checkCommand(cmd) {
  try {
    execSync(cmd, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

console.log("\n  CHERENKOV — API Conformance Testing\n");

if (!checkCommand("python3 --version")) {
  console.log("  Python 3 is required. Install from: https://python.org/downloads/\n");
  process.exit(1);
}

if (!checkCommand("pip3 --version") && !checkCommand("pip --version")) {
  console.log("  pip is required. Install from: https://pip.pypa.io/en/stable/installation/\n");
  process.exit(1);
}

try {
  execSync("pip3 install cherenkov", { stdio: "inherit" });
  console.log("\n  ✓ CHERENKOV installed successfully!\n");
  console.log("  Run `cherenkov doctor` to verify your setup.\n");
} catch {
  console.log("\n  Run: pip3 install cherenkov\n");
}
