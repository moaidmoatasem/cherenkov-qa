#!/usr/bin/env python3
"""
Memory Sync Bridge: CHERENKOV ↔ Qwen Code

Bridges the static `.qwen/memory/` seeds and Qwen Code's session memory
with CHERENKOV's Knowledge Repository (SQLite FTS5 + Redis vector cache).

Usage:
  python3 scripts/memory_sync.py [--dry-run]
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
QWEN_MEMORY_DIR = ROOT / ".qwen" / "memory"
CHERENKOV_DB_PATH = ROOT / "agent_memory" / "knowledge.db"
SYNC_DIR = ROOT / "agent_memory" / "sync"

def get_db_connection():
    # Ensure DB exists
    db_exists = CHERENKOV_DB_PATH.exists()
    conn = sqlite3.connect(CHERENKOV_DB_PATH)
    if not db_exists:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts 
            USING fts5(id, source, content, timestamp);
        """)
    return conn

def sync_qwen_seeds(conn, dry_run=False):
    """Sync static markdown seeds from .qwen/memory into FTS5."""
    print("Syncing static seeds...")
    if not QWEN_MEMORY_DIR.exists():
        print(f"Directory {QWEN_MEMORY_DIR} not found. Skipping.")
        return 0
        
    count = 0
    for md_file in QWEN_MEMORY_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        # Use content hash as ID to prevent duplicates if file doesn't change
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Check if already synced
        cur = conn.cursor()
        cur.execute("SELECT id FROM knowledge_fts WHERE id = ?", (doc_id,))
        if cur.fetchone():
            continue
            
        if not dry_run:
            conn.execute(
                "INSERT INTO knowledge_fts (id, source, content, timestamp) VALUES (?, ?, ?, ?)",
                (doc_id, f"qwen_seed:{md_file.name}", content, datetime.now().isoformat())
            )
            conn.commit()
        count += 1
    
    return count

def sync_session_decisions(conn, dry_run=False):
    """Sync decisions from agent_memory/sync/findings into FTS5."""
    print("Syncing session decisions...")
    findings_dir = SYNC_DIR / "findings"
    if not findings_dir.exists():
        return 0
        
    count = 0
    for finding_file in findings_dir.glob("*.json"):
        try:
            data = json.loads(finding_file.read_text(encoding="utf-8"))
            session_id = data.get("session_id", "unknown")
            
            for finding in data.get("findings", []):
                if finding.get("type") == "decision":
                    # Create a unique ID for this decision
                    content = finding.get("message", "")
                    ts = finding.get("timestamp", "")
                    doc_id = f"dec_{session_id}_{hashlib.md5((ts+content).encode()).hexdigest()[:8]}"
                    
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM knowledge_fts WHERE id = ?", (doc_id,))
                    if cur.fetchone():
                        continue
                        
                    if not dry_run:
                        conn.execute(
                            "INSERT INTO knowledge_fts (id, source, content, timestamp) VALUES (?, ?, ?, ?)",
                            (doc_id, f"session:{session_id}", content, ts)
                        )
                        conn.commit()
                    count += 1
        except Exception as e:
            print(f"Error processing {finding_file.name}: {e}")
            
    return count

def main():
    import sys
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("Running in DRY-RUN mode. No changes will be saved.")
        
    conn = get_db_connection()
    try:
        seed_count = sync_qwen_seeds(conn, dry_run)
        print(f"Added {seed_count} new static seeds to FTS5.")
        
        decision_count = sync_session_decisions(conn, dry_run)
        print(f"Added {decision_count} new decisions to FTS5.")
        
        print("Sync complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
