import subprocess, json

r = subprocess.run(['gh', 'issue', 'list', '--state', 'open', '--limit', '100', '--json', 'number,title,labels'], capture_output=True, text=True)
if r.stdout.strip():
    data = json.loads(r.stdout)
    if data:
        print(f'Total open issues: {len(data)}')
        for item in data:
            labels = ', '.join(l['name'] for l in item.get('labels', []))
            print(f"  #{item['number']}: {item['title'][:70]} [{labels}]")
    else:
        print('No open issues')
