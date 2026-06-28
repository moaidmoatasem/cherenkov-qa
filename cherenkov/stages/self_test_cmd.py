import os
import time
import subprocess
import requests
from cherenkov.core.settings import get_settings
from cherenkov.core.compat import npx as _npx, subprocess_env as _subprocess_env
from cherenkov.ai import get_client
from cherenkov.ai.ollama_client import strip_think

MINI_SPEC = {
    "path": "/self-test",
    "method": "GET",
    "operation": {"responses": {"200": {"description": "OK"}}},
    "schemas": {},
}


def run_self_test() -> int:
    print("=== CHERENKOV SELF-TEST ===")

    # 1. Check Ollama Reachable
    print("[1/3] Checking Ollama connectivity...", end=" ")
    try:
        t0 = time.time()
        base_url = get_settings().OLLAMA_URL.rsplit("/api/generate", 1)[0]
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        dt = int((time.time() - t0) * 1000)
        print(f"OK ({dt}ms)")
    except Exception as e:
        print(f"FAILED\nError: {e}")
        return 1

    # 2. Generate a Test
    print("[2/3] Generating test via Ollama...", end=" ")
    try:
        t0 = time.time()
        client = get_client()
        from cherenkov.stages.generate import SYSTEM_PROMPT

        user_prompt = "Generate a Playwright API test for GET /health asserting 200 OK using import { client } from '../client';"
        raw_code = client.complete_code(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=get_settings().GEN_MODEL,
            temperature=0.1,
        )
        code = strip_think(raw_code)
        if "from '../client'" not in code and "from '@playwright/test'" not in code:
            print("FAILED\nError: Generated code missing required imports.")
            return 1
        dt = int((time.time() - t0) * 1000)
        print(f"OK ({dt}ms)")
    except Exception as e:
        print(f"FAILED\nError: {e}")
        return 1

    # 3. TSC Compilation
    print("[3/3] Compiling test with tsc --noEmit...", end=" ")
    try:
        from pathlib import Path as _Path
        stub_dir = str(_Path(__file__).parent.parent.parent / "stub")
        temp_dir = os.path.join(stub_dir, "generated_tests")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "self_test.spec.ts")

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)

        t0 = time.time()
        process = subprocess.run(
            [_npx(), "tsc", "--noEmit"],
            cwd=stub_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=_subprocess_env(),
        )
        dt = int((time.time() - t0) * 1000)
        if os.path.exists(temp_file):
            os.remove(temp_file)

        if process.returncode != 0:
            # Filter to errors only in our self-test file — pre-existing errors
            # in other stub/generated_tests/*.spec.ts files must not block the check.
            our_errors = [
                line
                for line in (process.stdout + process.stderr).splitlines()
                if "self_test.spec.ts" in line
            ]
            if our_errors:
                print("FAILED\n" + "\n".join(our_errors[:5]))
                return 1
        print(f"OK ({dt}ms)")
    except Exception as e:
        print(f"FAILED\nError: {e}")
        return 1

    print("\nSELF-TEST PASSED. Core pipeline is healthy.")
    return 0
