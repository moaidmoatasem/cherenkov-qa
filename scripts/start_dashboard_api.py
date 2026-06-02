#!/usr/bin/env python3
import os, sys
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
DEFERRED_DIR = os.path.join(PROJECT_ROOT, "track-b-c-deferred")
sys.path = [p for p in sys.path if 'cherenkov-professional' not in p]
sys.path.insert(0, PROJECT_ROOT)
import cherenkov
deferred_cherenkov = os.path.join(DEFERRED_DIR, "cherenkov")
if deferred_cherenkov not in cherenkov.__path__:
    cherenkov.__path__.insert(0, deferred_cherenkov)
import importlib
api_mod = importlib.import_module("cherenkov.api.main")
app = api_mod.app
if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8080
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
