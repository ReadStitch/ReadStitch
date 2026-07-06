import urllib.request
import json
import os

req = urllib.request.Request('https://api.github.com/repos/ReadStitch/ReadStitch/releases', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        releases = json.loads(response.read().decode('utf-8'))
        for r in releases:
            print(f"=== {r.get('tag_name')} ===")
            print(r.get('body'))
except Exception as e:
    print("Error:", e)
