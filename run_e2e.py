import subprocess
import time
import urllib.request
import os

print('Starting uvicorn...')
env = os.environ.copy()
env['PYTHONPATH'] = '.'
api_proc = subprocess.Popen(['uvicorn', 'cherenkov.web.api:app', '--port', '8000'], env=env)

# Wait for API to boot
for _ in range(30):
    try:
        if urllib.request.urlopen('http://127.0.0.1:8000/api/health').getcode() == 200:
            print('API is up!')
            break
    except:
        time.sleep(0.5)
else:
    print('API failed to start.')
    api_proc.kill()
    exit(1)

print('Running Playwright...')
env['API_URL'] = 'http://127.0.0.1:8000'
pw_proc = subprocess.run(['npx', 'playwright', 'test'], cwd='playwright-suite', env=env)

api_proc.kill()
exit(pw_proc.returncode)
