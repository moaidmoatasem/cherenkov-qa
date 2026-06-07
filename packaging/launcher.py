import os
import sys
import threading
import time
import webbrowser
import socket
from contextlib import closing

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
    print("CHERENKOV: Starting engine...")
    
    # Run in demo mode by default if no ollama detected
    try:
        import subprocess
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

    time.sleep(2) # Wait for server to bind
    
    url = f"http://127.0.0.1:{port}"
    print(f"CHERENKOV: Opening dashboard in browser: {url}")
    webbrowser.open(url)
    
    print("CHERENKOV: Press Ctrl+C to shut down.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("CHERENKOV: Shutting down engine...")
        sys.exit(0)

if __name__ == "__main__":
    main()
