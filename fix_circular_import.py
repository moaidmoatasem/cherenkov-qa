import os
for root, _, files in os.walk('cherenkov/substrate/providers'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace(
                'from cherenkov.substrate.provider import ProviderCapabilities', 
                'from cherenkov.substrate.provider_base import ProviderCapabilities'
            ).replace(
                'from cherenkov.substrate.provider import ModelProvider', 
                'from cherenkov.substrate.provider_base import ModelProvider'
            )
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
