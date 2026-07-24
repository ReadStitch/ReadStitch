import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
    if match:
        print("NEXT_DATA found! Length:", len(match.group(1)))
        print(match.group(1)[:1500])
    else:
        print("No NEXT_DATA found")
        
    links = re.findall(r'href=[\'"](/series/[^\'"]+)[\'"]', html)
    print("Chapter links found:", len(links))
    print(links[:5])
except Exception as e:
    print("Error:", e)
