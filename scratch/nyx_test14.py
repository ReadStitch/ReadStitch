import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

slugs = re.findall(r'\\*"slug\\*":\\*"([^\\"]+)\\*"', html)
print("All slugs:")
for s in set(slugs):
    print(s)
