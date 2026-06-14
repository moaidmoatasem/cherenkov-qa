import os
import re

def main():
    repo_root = '/home/moaid/cherenkov-qa/cherenkov'
    for root, _, files in os.walk(repo_root):
        for f in files:
            if f.endswith('.py') and f != 'config.py' and f != 'settings.py':
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                if 'from cherenkov.core.config import Config' in content or 'Config.' in content:
                    content = re.sub(
                        r'from cherenkov\.core\.config import Config(?:\s+as\s+_Config)?',
                        'from cherenkov.core.settings import get_settings',
                        content
                    )
                    # Handle Config.ATTRIBUTE to get_settings().ATTRIBUTE
                    content = re.sub(r'\bConfig\.([A-Z0-9_]+)\b', r'get_settings().\1', content)
                    # Handle _Config.ATTRIBUTE if aliased
                    content = re.sub(r'\b_Config\.([A-Z0-9_]+)\b', r'get_settings().\1', content)
                    
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(content)
                        
    # Do the same for tests
    tests_root = '/home/moaid/cherenkov-qa/tests'
    for root, _, files in os.walk(tests_root):
        for f in files:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                if 'from cherenkov.core.config import Config' in content or 'Config.' in content:
                    content = re.sub(
                        r'from cherenkov\.core\.config import Config(?:\s+as\s+_Config)?',
                        'from cherenkov.core.settings import get_settings',
                        content
                    )
                    content = re.sub(r'\bConfig\.([A-Z0-9_]+)\b', r'get_settings().\1', content)
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(content)

if __name__ == '__main__':
    main()
