import os
for root, _, files in os.walk('.'):
    if '.git' in root or '.venv' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('cherenkov.substrate.providers.template_generator', 'cherenkov.substrate.providers.template_generator')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
