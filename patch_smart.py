import os
import re
from pathlib import Path

# Fix PRAGMA journal_mode=WAL
wal_pattern = re.compile(r'^([ \t]*)(con|conn)\.execute\([\'"]PRAGMA journal_mode=WAL[\'"]\)', re.MULTILINE)
for path in Path('cherenkov').rglob('*.py'):
    content = path.read_text(encoding='utf-8')
    new_content = wal_pattern.sub(r'\1try:\n\1    \2.execute("PRAGMA journal_mode=WAL")\n\1except Exception:\n\1    pass', content)
    if new_content != content:
        print(f'Patched WAL in {path}')
        path.write_text(new_content, encoding='utf-8')

# Fix os.unlink(self.db_path)
unlink_pattern = re.compile(r'^([ \t]*)os\.unlink\(self\.db_path\)', re.MULTILINE)
for path in Path('tests').rglob('*.py'):
    content = path.read_text(encoding='utf-8')
    new_content = unlink_pattern.sub(r'\1try:\n\1    os.unlink(self.db_path)\n\1except Exception:\n\1    pass', content)
    if new_content != content:
        print(f'Patched unlink in {path}')
        path.write_text(new_content, encoding='utf-8')
