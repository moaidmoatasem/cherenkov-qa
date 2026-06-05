import urllib.request, json
token = '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'
url = 'https://api.github.com/repos/moaidmoatasem/cherenkov-qa/issues?state=open&per_page=100'
req = urllib.request.Request(url, headers={'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json'})
try:
    with urllib.request.urlopen(req) as response:
        issues = json.loads(response.read().decode())
        for i in issues:
            if 'pull_request' not in i:
                print(f"#{i['number']}: {i['title']}")
except Exception as e:
    print(e)
