import os
import re

def fix_api_py():
    path = "cherenkov/web/api.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # rename route
    content = content.replace("async def get_settings():\n    return _settings", "async def api_get_settings():\n    return _settings")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def fix_test_patches():
    tests_dir = "tests"
    for root, _, files in os.walk(tests_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as f_in:
                    content = f_in.read()
                
                # Replace @patch("...get_settings().FIELD", VAL)
                # with @patch.object(get_settings(), "FIELD", VAL)
                # We need to ensure get_settings is imported.
                if 'get_settings().' in content and '@patch' in content:
                    # First, ensure import
                    if "from cherenkov.core.settings import get_settings" not in content:
                        content = "from cherenkov.core.settings import get_settings\n" + content
                    if "from unittest.mock import patch" in content and "patch.object" not in content:
                        pass # patch.object is on patch
                        
                    # Regex to match @patch("any.path.get_settings().FIELD", VAL)
                    # We have to be careful with newlines and parentheses.
                    content = re.sub(
                        r'@patch\([\'"][a-zA-Z0-9_\.]+\.get_settings\(\)\.([a-zA-Z0-9_]+)[\'"]\s*,\s*([^\)]+)\)',
                        r'@patch.object(get_settings(), "\1", \2)',
                        content
                    )
                    with open(path, "w", encoding="utf-8") as f_out:
                        f_out.write(content)

def fix_config_name_errors():
    tests_dir = "tests"
    for root, _, files in os.walk(tests_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as f_in:
                    content = f_in.read()
                
                changed = False
                if 'Config()' in content:
                    content = content.replace('Config()', 'get_settings()')
                    changed = True
                if 'Config.' in content:
                    content = content.replace('Config.', 'get_settings().')
                    changed = True
                # if there is just `Config` as a class reference
                if re.search(r'\bConfig\b', content) and 'get_settings' in content:
                    content = re.sub(r'\bConfig\b', 'type(get_settings())', content)
                    changed = True
                
                if changed:
                    with open(path, "w", encoding="utf-8") as f_out:
                        f_out.write(content)

if __name__ == "__main__":
    fix_api_py()
    fix_test_patches()
    fix_config_name_errors()
    print("Fixes applied.")
