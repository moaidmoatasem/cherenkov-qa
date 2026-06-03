#!/usr/bin/env python3
import urllib.request
import urllib.error
import json

TOKEN = "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"
OWNER, REPO = "moaidmoatasem", "cherenkov-qa"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"

H = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "cherenkov-closer"
}

def post_comment_and_close(issue_num, comment_body):
    # 1. Post comment
    comment_url = f"{API}/{issue_num}/comments"
    data = json.dumps({"body": comment_body}).encode()
    req = urllib.request.Request(comment_url, data=data, headers=H, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            print(f"Posted comment on #{issue_num}: {r.status}")
    except urllib.error.HTTPError as e:
        print(f"Error commenting #{issue_num}: {e.code} - {e.read().decode()}")

    # 2. Close issue
    close_url = f"{API}/{issue_num}"
    data = json.dumps({"state": "closed"}).encode()
    req = urllib.request.Request(close_url, data=data, headers=H, method="PATCH")
    try:
        with urllib.request.urlopen(req) as r:
            print(f"Closed #{issue_num}: {r.status}")
    except urllib.error.HTTPError as e:
        print(f"Error closing #{issue_num}: {e.code} - {e.read().decode()}")

def main():
    issues_to_close = {
        85: "[E7-1] Implemented in cherenkov/reflector/store.py (VerdictStore and SQLite SQLite persistence layer). Smoke and unit tests green.",
        86: "[E7-2] Implemented in cherenkov/reflector/reflector.py (rerank() with verdict reweighting). Verified with clean test suite.",
        87: "[E7-3] Implemented in cherenkov/reflector/reflector.py (decay scoring, confirm count, and idiom upsert logic). Verified with clean test suite.",
        88: "[E7-4] Wired Reflector and VerdictStore into proof_run.py loop with CLI options (--reflector and --reflector-stats).",
        84: "[EPIC] Epoch 7 Reflector and Verdict Memory successfully implemented. All sub-tasks (85-88) are completed and pushed to main.",
        96: "[FE-0] Implemented shared UI primitives and consistency gallery in track-b-c-deferred/dashboard. Verified builds and design conformance."
    }

    for num, comment in issues_to_close.items():
        print(f"\nProcessing Issue #{num}...")
        post_comment_and_close(num, comment)

if __name__ == "__main__":
    main()
