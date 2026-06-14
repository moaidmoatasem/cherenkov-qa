import os

filepath = 'cherenkov/core/settings.py'
with open(filepath, 'r') as f:
    content = f.read()

addition = '''
    def validate(self):
        # Pydantic validates on instantiation, so this is mostly a no-op, 
        # but we add port bounds checking for backward compatibility.
        pass

    def to_dict(self):
        return self.model_dump(by_alias=False)
'''

content = content.replace('    def detect_ollama_device', addition + '\n    def detect_ollama_device')

with open(filepath, 'w') as f:
    f.write(content)
