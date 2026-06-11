"""
CHERENKOV launcher — PyInstaller sidecar entry point.

Communicates with the Tauri host via NDJSON on stdout.
Every line printed as JSON is an event; plain text lines are ignored by Tauri.

Protocol (all NDJSON, one JSON object per line):
  {"event": "ready",     "data": {"version": "1.0.0"}}
  {"event": "port",      "data": {"port": 8432}}
  {"event": "demo_mode", "data": {"reason": "Ollama not found"}}
  {"event": "progress",  "data": {"step": "model_pull", "pct": 42, "detail": "..."}}
  {"event": "shutdown",  "data": {"signal": "SIGINT"}}
"""
import os
import sys
import json
import signal
import threading
import time
import webbrowser
import socket
import subprocess
from contextlib import closing

VERSION = "1.0.0"


def emit(event_type: str, data: dict):
    """Emit a single NDJSON event line to stdout (Tauri sidecar protocol)."""
    print(json.dumps({"event": event_type, "data": data}), flush=True)


def find_free_port(start_port: int = 8000) -> int:
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1


def run_server(port: int) -> None:
    import uvicorn
    from cherenkov.web.api import app as fastapi_app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")


def _check_ollama() -> bool:
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> None:
    no_browser = os.environ.get("CHERENKOV_NO_BROWSER", "0") == "1"

    def _signal_handler(sig, _frame):
        emit("shutdown", {"signal": str(sig)})
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    emit("ready", {"version": VERSION})

    # Ollama availability check
    if not _check_ollama():
        os.environ["DEMO_MODE"] = "1"
        emit("demo_mode", {"reason": "Ollama not found — running in demo mode"})

    if os.environ.get("DEMO_MODE") == "1":
        try:
            from cherenkov.execution.demo_mode import generate_demo_findings
            generate_demo_findings()
        except Exception:
            pass

    port = find_free_port(8000)

    # Emit port BEFORE starting the server so Tauri can begin health polling
    emit("port", {"port": port})

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready (basic health check)
    for _ in range(20):
        time.sleep(0.5)
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            break
        except Exception:
            continue

    if not no_browser:
        webbrowser.open(f"http://127.0.0.1:{port}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        emit("shutdown", {"signal": "SIGINT"})
        sys.exit(0)


if __name__ == "__main__":
    main()
