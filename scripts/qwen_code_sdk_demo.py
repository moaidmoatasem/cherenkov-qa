#!/usr/bin/env python3
"""
Qwen Code SDK Demo

A small script that demonstrates invoking Qwen Code via Python subprocess
(since Qwen Code is Node-based, we interact with its CLI or MCP).
"""

import subprocess


def generate_test_snippet(prompt: str) -> str:
    print(f"Asking Qwen Code: {prompt}")
    cmd = ["qwen", "-p", prompt]
    try:
        # Run headless
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running Qwen Code: {e.stderr}"


if __name__ == "__main__":
    prompt = "Write a basic pytest function that asserts 1 + 1 == 2. Output only code."
    print("--- Output ---")
    print(generate_test_snippet(prompt))
