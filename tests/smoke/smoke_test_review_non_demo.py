#!/usr/bin/env python3
"""
smoke_test_review_non_demo.py — verifies cherenkov.py review boots without --demo flag.
"""

import os
import subprocess
import time
import requests


def main():
    print("Starting review dashboard in non-demo mode...")
    proc = subprocess.Popen(
        ["python3", "cherenkov.py", "review", "--port", "8005"],
        env={**os.environ, "PYTHONPATH": "."},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    healthy = False
    for _ in range(30):
        try:
            resp = requests.get("http://localhost:8005/", timeout=2)
            if resp.status_code == 200:
                healthy = True
                print("Dashboard is healthy and online.")
                break
        except Exception:
            time.sleep(1)

    proc.terminate()
    proc.wait(timeout=5)

    if not healthy:
        stdout, stderr = proc.communicate()
        print(f"Stdout:\n{stdout.decode()}")
        print(f"Stderr:\n{stderr.decode()}")
        assert False, "Review dashboard failed to boot in non-demo mode."

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
