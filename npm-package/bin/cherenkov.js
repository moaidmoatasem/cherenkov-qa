#!/usr/bin/env node

const { execSync } = require("child_process");
const args = process.argv.slice(2).join(" ");

try {
  execSync("cherenkov " + args, { stdio: "inherit" });
} catch (err) {
  process.exit(err.status || 1);
}
