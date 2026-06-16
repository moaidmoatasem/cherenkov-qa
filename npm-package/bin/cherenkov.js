#!/usr/bin/env node

const { spawnSync } = require("child_process");

const result = spawnSync("cherenkov", process.argv.slice(2), { stdio: "inherit" });

if (result.error) {
  console.error("cherenkov not found on PATH — run: pip install cherenkov");
  process.exit(1);
}

process.exit(result.status ?? 0);
