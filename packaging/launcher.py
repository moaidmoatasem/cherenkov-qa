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


def emit_event(event_type: str, data: dict):
    event = {"event": event_type, "data": data}
    print(json.dumps(event), flush=True)


def find_free_port(start_port=8000):
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1


def run_server(port):
    import uvicorn
    from cherenkov.web.api import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    no_browser = os.environ.get("CHERENKOV_NO_BROWSER", "0") == "1"

    def signal_handler(sig, frame):
        emit_event("shutdown", {"signal": sig})
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emit_event("ready", {"version": "0.1.0"})

    print("CHERENKOV: Starting engine...")

    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=2)
        if result.returncode != 0:
            raise Exception("Ollama not running")
    except Exception:
        print("CHERENKOV: Ollama not found or not running. Enabling DEMO_MODE.")
        os.environ['DEMO_MODE'] = '1'

    if os.environ.get('DEMO_MODE') == '1':
        from cherenkov.execution.demo_mode import generate_demo_findings
        print("CHERENKOV: Loading demo findings into HITL queue...")
        generate_demo_findings()

    port = find_free_port(8000)
    print(f"CHERENKOV: Engine running on http://127.0.0.1:{port}")

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    time.sleep(2)

    if not no_browser:
        url = f"http://127.0.0.1:{port}"
        print(f"CHERENKOV: Opening dashboard in browser: {url}")
        webbrowser.open(url)
    else:
        print("CHERENKOV: Sidecar mode (no browser)")

    print("CHERENKOV: Press Ctrl+C to shut down.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("CHERENKOV: Shutting down engine...")
        emit_event("shutdown", {"signal": "SIGINT"})
        sys.exit(0)


if __name__ == "__main__":
    main()
