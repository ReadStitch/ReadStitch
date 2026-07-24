import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

match = re.search(r'.{0,100}\"slug\":\"chapter-2\".{0,100}', html)
if match:
    print("Context around chapter 2 slug:")
    print(match.group(0))
