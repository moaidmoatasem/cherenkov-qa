# CHERENKOV-QA Data Migration Strategy

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #277 (Phase -1), #279 (Phase 0b)

---

## Schema Versioning Strategy

Every SQLite table has a `schema_version` column (default 1). Migrations run on app startup. Migrations are idempotent (can be run multiple times safely). Pre-migration backup is created automatically.

---

## Migration Framework

```python
# cherenkov/core/migration.py
from dataclasses import dataclass
from typing import Callable
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

@dataclass
class Migration:
    version: int
    description: str
    up: Callable[[sqlite3.Connection], None]
    down: Callable[[sqlite3.Connection], None]

class MigrationRunner:
    def __init__(self, db_path: str, migrations: list[Migration]):
        self.db_path = db_path
        self.migrations = sorted(migrations, key=lambda m: m.version)
        self.backup_dir = Path(".cherenkov/backups")

    def get_current_version(self, conn: sqlite3.Connection) -> int:
        try:
            cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.OperationalError:
            return 0

    def backup(self, version: int) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{timestamp}_v{version}_pre_migration.db"
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def migrate(self) -> None:
        conn = sqlite3.connect(self.db_path)
        current_version = self.get_current_version(conn)

        # Create schema_version table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        for migration in self.migrations:
            if migration.version <= current_version:
                continue

            print(f"Applying migration v{migration.version}: {migration.description}")

            # Backup before migration
            backup_path = self.backup(current_version)
            print(f"  Backup created: {backup_path}")

            try:
                # Apply migration
                migration.up(conn)

                # Record migration
                conn.execute(
                    "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                    (migration.version, migration.description)
                )
                conn.commit()

                print(f"  Migration v{migration.version} applied successfully")
                current_version = migration.version

            except Exception as e:
                print(f"  Migration v{migration.version} failed: {e}")
                print(f"  Restoring from backup: {backup_path}")
                conn.close()
                shutil.copy2(backup_path, self.db_path)
                raise

        conn.close()

    def rollback(self, target_version: int) -> None:
        conn = sqlite3.connect(self.db_path)
        current_version = self.get_current_version(conn)

        if target_version >= current_version:
            print(f"Already at version {current_version}, nothing to rollback")
            conn.close()
            return

        # Rollback migrations in reverse order
        for migration in reversed(self.migrations):
            if migration.version <= target_version:
                break
            if migration.version > current_version:
                continue

            print(f"Rolling back migration v{migration.version}: {migration.description}")

            try:
                migration.down(conn)
                conn.execute("DELETE FROM schema_version WHERE version = ?", (migration.version,))
                conn.commit()
                print(f"  Migration v{migration.version} rolled back successfully")
            except Exception as e:
                print(f"  Rollback v{migration.version} failed: {e}")
                conn.close()
                raise

        conn.close()
```

---

## Rollback Strategy

1. **Before any migration**: snapshot affected .db files to `.cherenkov/backups/{date}_{version}_pre_migration/`
2. **Run `up()`**: Verify with assertion queries
3. **If `up()` fails**: restore from snapshot, log error, exit
4. **If user wants to rollback**: `cherenkov db rollback --version <vN>` runs `down()`
5. **Rollback is user-initiated** (CLI only). Never auto-rollback

---

## v1 → v2 Migrations

| Table | Change | Migration |
|-------|--------|-----------|
| `verdicts` | Add `classification` column | `ALTER TABLE verdicts ADD COLUMN classification TEXT DEFAULT 'api_bug'` |
| `idioms` | Add `vlm_tier` column | `ALTER TABLE idioms ADD COLUMN vlm_tier TEXT DEFAULT 'small_vlm'` |
| `device_targets` | New table | `CREATE TABLE device_targets (...)` |
| `truth_model` | New table (persistence) | `CREATE TABLE truth_model (...)` |
| `conversations` | New table (chat memory) | `CREATE TABLE conversations (...)` |

### Migration 001: Add VLM Tier

```python
# migrations/001_add_vlm_tier.py
def up(conn: sqlite3.Connection):
    conn.execute("ALTER TABLE idioms ADD COLUMN vlm_tier TEXT DEFAULT 'small_vlm'")

def down(conn: sqlite3.Connection):
    # SQLite doesn't support DROP COLUMN, so we recreate the table
    conn.execute("""
        CREATE TABLE idioms_new AS
        SELECT id, pattern, weight, created_at
        FROM idioms
    """)
    conn.execute("DROP TABLE idioms")
    conn.execute("ALTER TABLE idioms_new RENAME TO idioms")

migration = Migration(
    version=1,
    description="Add vlm_tier column to idioms",
    up=up,
    down=down
)
```

### Migration 002: Add Device Targets

```python
# migrations/002_add_device_targets.py
def up(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE device_targets (
            device_id TEXT PRIMARY KEY,
            device_class TEXT NOT NULL,
            platform TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def down(conn: sqlite3.Connection):
    conn.execute("DROP TABLE device_targets")

migration = Migration(
    version=2,
    description="Add device_targets table",
    up=up,
    down=down
)
```

### Migration 003: Add Truth Model Persistence

```python
# migrations/003_add_truth_model.py
def up(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE truth_model (
            claim_id TEXT PRIMARY KEY,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER,
            confidence REAL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def down(conn: sqlite3.Connection):
    conn.execute("DROP TABLE truth_model")

migration = Migration(
    version=3,
    description="Add truth_model table for persistence",
    up=up,
    down=down
)
```

### Migration 004: Add Conversations

```python
# migrations/004_add_conversations.py
def up(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE conversations (
            session_id TEXT PRIMARY KEY,
            messages TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def down(conn: sqlite3.Connection):
    conn.execute("DROP TABLE conversations")

migration = Migration(
    version=4,
    description="Add conversations table for chat memory",
    up=up,
    down=down
)
```

---

## Migration Rules

1. **Every migration has `up()` AND `down()`**
2. **Migrations are numbered**: `001_add_vlm_tier.py`, `002_add_device_targets.py`
3. **Backup before migration** (copy .db file)
4. **If migration fails, app exits with clear error message**
5. **`cherenkov db migrate` runs all pending migrations**
6. **`cherenkov db rollback --version v1` rolls back to v1**

---

## CLI Commands

### Migrate
```bash
cherenkov db migrate
```

Applies all pending migrations. Creates backup before each migration.

### Rollback
```bash
cherenkov db rollback --version 1
```

Rolls back to version 1. Runs `down()` for each migration in reverse order.

### Status
```bash
cherenkov db status
```

Shows current schema version and list of applied migrations.

---

## Auto-Migration on Startup

```python
# cherenkov/core/orchestrator.py
def run_pipeline(self, spec_path: str):
    # Run migrations on startup
    from cherenkov.core.migration import MigrationRunner
    from migrations import get_migrations

    runner = MigrationRunner("data/cherenkov.db", get_migrations())
    runner.migrate()

    # ... rest of pipeline ...
```

---

## Testing Migrations

```python
# tests/unit/test_migration.py
import sqlite3
from cherenkov.core.migration import MigrationRunner
from migrations import get_migrations

def test_migrations_apply_cleanly():
    """All migrations should apply without errors."""
    conn = sqlite3.connect(":memory:")
    runner = MigrationRunner(":memory:", get_migrations())
    runner.migrate()

    # Verify schema_version table exists
    cursor = conn.execute("SELECT version FROM schema_version")
    versions = [row[0] for row in cursor.fetchall()]

    assert versions == [1, 2, 3, 4]

def test_migrations_are_idempotent():
    """Running migrations twice should be safe."""
    conn = sqlite3.connect(":memory:")
    runner = MigrationRunner(":memory:", get_migrations())

    runner.migrate()
    runner.migrate()  # Should not fail

    cursor = conn.execute("SELECT version FROM schema_version")
    versions = [row[0] for row in cursor.fetchall()]

    assert versions == [1, 2, 3, 4]

def test_rollback_works():
    """Rollback should reverse migrations."""
    conn = sqlite3.connect(":memory:")
    runner = MigrationRunner(":memory:", get_migrations())

    runner.migrate()
    runner.rollback(target_version=2)

    cursor = conn.execute("SELECT version FROM schema_version")
    versions = [row[0] for row in cursor.fetchall()]

    assert versions == [1, 2]
```

---

## References

- EPIC #279 (Phase 0b: Foundations)
- Issue #321 (Migration framework)
- `cherenkov/core/migration.py` (to be created)
- `migrations/` (to be created)
