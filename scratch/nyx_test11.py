import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

for match in re.finditer(r'.{0,30}chapter-2(?!\d).{0,30}', html):
    print("MATCH:", match.group(0))
