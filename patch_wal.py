import os
import glob
from pathlib import Path

for path in Path('.').rglob('*.py'):
    content = path.read_text(encoding='utf-8')
    if 'PRAGMA journal_mode=WAL' in content:
        new_content = content.replace(
            'con.execute(\"PRAGMA journal_mode=WAL\")',
            'try:\n            con.execute(\"PRAGMA journal_mode=WAL\")\n        except sqlite3.OperationalError:\n            pass'
        ).replace(
            'conn.execute(\"PRAGMA journal_mode=WAL\")',
            'try:\n                conn.execute(\"PRAGMA journal_mode=WAL\")\n            except sqlite3.OperationalError:\n                pass'
        )
        if new_content != content:
            print(f'Patched {path}')
            path.write_text(new_content, encoding='utf-8')
