import urllib.request
import re
import json

url = 'https://nyxscans.com/series/romance-starting-with-parenting/chapter-28'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
if match:
    data = json.loads(match.group(1))
    print("NEXT_DATA found!")
    # Look for pages in the json
    import pprint
    
    def find_pages(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'pages' or k == 'images' or k == 'chapter':
                    print(f"Found key {k}: {str(v)[:200]}")
                if isinstance(v, (dict, list)):
                    find_pages(v)
        elif isinstance(obj, list):
            for i in obj:
                find_pages(i)
                
    find_pages(data)
    
    # Just in case, let's dump all strings that end in webp or png
    webps = re.findall(r'[\'"]([^\'"]+\.(?:webp|png|jpg))[\'"]', html)
    print("Webp/png files in HTML:")
    for w in set(webps):
        if 'upload' in w:
            print(w)
else:
    print("No NEXT_DATA found")
