import urllib.request, json, os
token = os.environ.get('GITHUB_TOKEN', '')
url = 'https://api.github.com/repos/moaidmoatasem/cherenkov-qa/issues?state=open&per_page=100'
req = urllib.request.Request(url, headers={'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json'})
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        issues = json.loads(response.read().decode())
        for i in issues:
            if 'pull_request' not in i:
                print(f"#{i['number']}: {i['title']}")
except Exception as e:
    print(e)
