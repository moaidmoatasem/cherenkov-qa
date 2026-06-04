"""
cherenkov/stages/review_serve.py

Serves the Horizon V frontend UI (from ui_dist) and provides an API for fetching/updating HITL items.
"""
from __future__ import annotations

import http.server
import socketserver
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from cherenkov.hitl.store import HitlQueue
from cherenkov.core.feedback_store import FeedbackStore, FeedbackEntry

logger = logging.getLogger(__name__)

PORT = 8080
UI_DIST_DIR = Path(__file__).parent.parent.parent / "ui_dist"

class ReviewHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIST_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/hitl/pending":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            queue = HitlQueue()
            items = queue.list_pending()
            data = {"ok": True, "items": [i.model_dump() for i in items]}
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
            
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/hitl/action":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            
            item_id = req.get("id")
            action = req.get("action")
            reason = req.get("reason")
            
            queue = HitlQueue()
            store = FeedbackStore()
            
            if action == "approve":
                queue.approve(item_id, actor="frontend_ui", source="ui")
                store.record_feedback(FeedbackEntry(item_id, "approve"))
            elif action == "reject":
                queue.reject(item_id, actor="frontend_ui", source="ui")
                store.record_feedback(FeedbackEntry(item_id, "reject", reason=reason))
                
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            return
            
        self.send_error(404, "Not found")

def run_review_server() -> int:
    """Execute `cherenkov review`."""
    if not UI_DIST_DIR.exists():
        UI_DIST_DIR.mkdir(parents=True, exist_ok=True)
        # Create a stub index.html if it doesn't exist
        index_path = UI_DIST_DIR / "index.html"
        if not index_path.exists():
            with open(index_path, "w") as f:
                f.write("<html><body><h1>Cherenkov Review UI (Stub)</h1></body></html>")
                
    print(f"Starting CHERENKOV Review UI at http://localhost:{PORT}")
    try:
        with socketserver.TCPServer(("", PORT), ReviewHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    except OSError as e:
        print(f"Error starting server: {e}")
        return 1
    return 0
