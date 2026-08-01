import sys
import yaml

files = ['action.yml', '.github/workflows/demo-action.yml']
success = True

for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        print(f"SUCCESS: {fpath} parsed successfully.")
        print(f"  Root keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    except Exception as e:
        print(f"ERROR: {fpath} failed YAML parsing: {e}")
        success = False

if not success:
    sys.exit(1)
