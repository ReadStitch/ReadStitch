import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# Search for slugs in NextJS serialized data
slugs = re.findall(r'\\*"slug\\*":\\*"([^\\"]+)\\*"', html)
print("Slugs found:", len(slugs))
print(slugs[:30])

# Just generic slug extraction
slugs2 = re.findall(r'\"slug\":\"([^\"]+)\"', html)
print("Slugs2 found:", len(slugs2))
