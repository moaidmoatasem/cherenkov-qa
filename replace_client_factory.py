import os
import re

for root, _, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex to replace 'from cherenkov.substrate.client_factory import X, Y' to 'from cherenkov.substrate.client_factory import X, Y'
            # But only for get_client, set_client, reset_client, get_accounting_report, get_cache_stats
            # Let's just do a simple replace since we removed cherenkov.ai entirely.
            new_content = content.replace('from cherenkov.substrate.client_factory import', 'from cherenkov.substrate.client_factory import')
            new_content = new_content.replace('import cherenkov.substrate.client_factory as', 'import cherenkov.substrate.client_factory as')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
