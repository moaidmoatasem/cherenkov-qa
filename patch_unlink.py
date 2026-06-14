import os
import glob
from pathlib import Path

for path in Path('tests').rglob('*.py'):
    content = path.read_text(encoding='utf-8')
    if 'os.unlink(self.db_path)' in content:
        new_content = content.replace(
            'os.unlink(self.db_path)',
            'try:\n            os.unlink(self.db_path)\n        except OSError:\n            pass'
        )
        if new_content != content:
            print(f'Patched {path}')
            path.write_text(new_content, encoding='utf-8')
