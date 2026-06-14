import os
import re

tests_dir = r'/home/moaid/cherenkov-qa/tests'

patch_decorator_re = re.compile(r'@patch\([\"\']cherenkov\.[^\"\']+\.get_settings\(\)\.([A-Z0-9_]+)[\"\']\s*,\s*(.*?)\)')
patch_context_re = re.compile(r'patch\([\"\']cherenkov\.[^\"\']+\.get_settings\(\)\.([A-Z0-9_]+)[\"\']\s*,\s*(.*?)\)')

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    orig_content = content
    
    if patch_decorator_re.search(content) or patch_context_re.search(content):
        if 'from cherenkov.core.settings import get_settings' not in content:
            content = 'from cherenkov.core.settings import get_settings\n' + content
            
        content = patch_decorator_re.sub(r'@patch.object(get_settings(), "\1", \2)', content)
        content = patch_context_re.sub(r'patch.object(get_settings(), "\1", \2)', content)

    if content != orig_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f'Fixed {filepath}')

for root, _, files in os.walk(tests_dir):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))
