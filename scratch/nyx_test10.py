import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# Let's find all occurrences of the slug in the HTML
matches = re.findall(r'(/series/romance-starting-with-parenting/[^\'\"\\<>\s]+)', html)
matches_escaped = re.findall(r'(\\/series\\/romance-starting-with-parenting\\/[^\'\"\\<>\s]+)', html)

all_matches = set(matches + [m.replace('\\/', '/') for m in matches_escaped])
chap_links = [m for m in all_matches if 'chapter' in m]

def get_num(l):
    m = re.search(r'chapter-([\d\.]+)', l)
    return float(m.group(1)) if m else 0.0
    
print("Chapters found via broad search:", sorted([l.split('/')[-1] for l in chap_links], key=get_num))
print("Total chapters:", len(chap_links))
