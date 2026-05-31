#!/usr/bin/env python3
"""
cherenkov_validate.py — Backward-compatible wrapper delegating to unified cherenkov CLI.
Authority: v3.1 + delta.
"""
import sys
import subprocess

def main():
    # Forward the arguments directly to "python3 cherenkov.py validate"
    cmd = ["python3", "cherenkov.py", "validate"] + sys.argv[1:]
    
    process = subprocess.run(
        cmd,
        capture_output=False
    )
    sys.exit(process.returncode)

if __name__ == "__main__":
    main()
