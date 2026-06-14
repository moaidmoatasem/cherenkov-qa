import os
import re

def fix_all():
    tests_dir = 'tests'
    for root, _, files in os.walk(tests_dir):
        for f in files:
            if not f.endswith('.py'): continue
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as f_in:
                content = f_in.read()
            
            orig = content
            
            # Use a regex that finds patch( '...' )
            content = re.sub(
                r'patch\([\'\"][a-zA-Z0-9_\.]+\.get_settings\(\)\.([a-zA-Z0-9_]+)[\'\"]',
                r'patch.object(get_settings(), "\1"',
                content
            )
            
            if content != orig:
                if 'from cherenkov.core.settings import get_settings' not in content:
                    content = 'from cherenkov.core.settings import get_settings\n' + content
                with open(path, 'w', encoding='utf-8') as f_out:
                    f_out.write(content)
                print(f'Fixed {path}')

fix_all()
