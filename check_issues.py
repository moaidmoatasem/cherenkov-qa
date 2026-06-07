import json

with open('issues_dump.json', encoding='utf-8') as f:
    data = json.load(f)

for k, v in data.items():
    if 'error' in v:
        print(f"{k}: {v['error']}")
    else:
        print(f"{k}: {v.get('state')} - {v.get('title')}")
