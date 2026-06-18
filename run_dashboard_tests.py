#!/usr/bin/env python3
# DEPRECATED: track-b-c-deferred/ was re-integrated and deleted.
# Dashboard now lives in cherenkov/web/. This script is dead code.
import os
import sys
import subprocess
import time
import urllib.request
import urllib.error


def wait_for_port(port, timeout=30):
    url = f"http://127.0.0.1:{port}"
    print(f"Waiting for port {port} to be available...")
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if (
                    response.status == 200
                    or response.status == 404
                    or response.status == 500
                ):
                    print(f"Port {port} is healthy.")
                    return True
        except urllib.error.HTTPError as e:
            # Server responded, which means it is up!
            print(f"Port {port} responded with HTTP status {e.code}.")
            return True
        except Exception:
            time.sleep(1.0)
    print(f"Timeout waiting for port {port}.")
    return False


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    dashboard_dir = os.path.join(project_root, "track-b-c-deferred", "dashboard")

    # 1. Install packages and playwright if necessary
    print("Installing packages and checking Playwright setup...")
    subprocess.run(["npm", "install"], cwd=dashboard_dir, check=True)
    subprocess.run(
        ["npx", "playwright", "install", "chromium"], cwd=dashboard_dir, check=True
    )

    # 2. Boot up Backend on port 8000
    backend_script = os.path.join(project_root, "scripts", "start_dashboard_api.py")
    print("Booting up backend server on port 8000...")
    backend_log = open(
        os.path.join(project_root, "backend_test.log"), "w", encoding="utf-8"
    )
    backend_err = open(
        os.path.join(project_root, "backend_test.err"), "w", encoding="utf-8"
    )

    backend_proc = subprocess.Popen(
        ["python3", backend_script, "--port", "8000"],
        stdout=backend_log,
        stderr=backend_err,
        cwd=project_root,
    )

    # 3. Boot up Frontend on port 3000
    print("Booting up frontend Vite server on port 3000...")
    frontend_log = open(
        os.path.join(project_root, "frontend_test.log"), "w", encoding="utf-8"
    )
    frontend_err = open(
        os.path.join(project_root, "frontend_test.err"), "w", encoding="utf-8"
    )

    # We use npm run dev which starts vite
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        stdout=frontend_log,
        stderr=frontend_err,
        cwd=dashboard_dir,
    )

    success = False
    try:
        # Wait for both ports to become active
        if wait_for_port(8000) and wait_for_port(3000):
            print("\nBoth servers are active. Initiating Playwright E2E execution...")
            # Run Playwright tests
            test_res = subprocess.run(["npx", "playwright", "test"], cwd=dashboard_dir)
            success = test_res.returncode == 0
        else:
            print("Failed to start either frontend or backend server.")
            success = False
    except KeyboardInterrupt:
        print("Tests interrupted by user.")
    finally:
        print("\nShutting down frontend server...")
        frontend_proc.terminate()
        frontend_proc.wait()
        frontend_log.close()
        frontend_err.close()

        print("Shutting down backend server...")
        backend_proc.terminate()
        backend_proc.wait()
        backend_log.close()
        backend_err.close()

    print(f"\nDashboard E2E run completed. Status: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
