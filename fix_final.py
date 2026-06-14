import os, re

# Fix orchestrator
with open('cherenkov/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()
if 'from cherenkov.core.settings import get_settings' not in content:
    content = 'from cherenkov.core.settings import get_settings\n' + content
content = content.replace('Config.detect_ollama_device(', 'get_settings().detect_ollama_device(')
with open('cherenkov/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Fix test_api_endpoints.py
with open('tests/integration/test_api_endpoints.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace(
    '@patch("cherenkov.core.config.get_settings().detect_ollama_device", return_value="cpu")',
    '@patch.object(get_settings(), "detect_ollama_device", return_value="cpu")'
)
# And maybe there's another one inside a string
content = content.replace(
    '"cherenkov.core.config.get_settings().detect_ollama_device"',
    '"cherenkov.core.settings.CherenkovSettings.detect_ollama_device"'
)
with open('tests/integration/test_api_endpoints.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Fix web/api.py
with open('cherenkov/web/api.py', 'r', encoding='utf-8') as f:
    api_content = f.read()
# Find: configured_key = get_settings().HITL_API_KEY
# and inside verify_key: replace configured_key with get_settings().HITL_API_KEY
# Then remove the global configured_key = ...
import re
api_content = re.sub(r'configured_key = get_settings\(\)\.HITL_API_KEY\n?', '', api_content)
api_content = re.sub(r'\bconfigured_key\b', 'get_settings().HITL_API_KEY', api_content)
with open('cherenkov/web/api.py', 'w', encoding='utf-8') as f:
    f.write(api_content)
