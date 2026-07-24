import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    links = re.findall(r'href=[\'"](/series/romance-starting-with-parenting[^\'"]*)[\'"]', html)
    unique_links = set(links)
    chapter_links = [l for l in unique_links if 'chapter' in l]
    
    def get_num(l):
        m = re.search(r'chapter-([\d\.]+)', l)
        return float(m.group(1)) if m else 0.0
        
    chapter_links = sorted(chapter_links, key=get_num)
    print("Chapters found:", [l.split('/')[-1] for l in chapter_links])
    
    # Try finding next_f data
    matches = re.findall(r'self\.__next_f\.push\(\[([^\]]+)\]\)', html)
    print(f"Next_f pushes found: {len(matches)}")
    # See if there's any unescaped chapter URLs in the entire HTML that aren't in hrefs
    import json
    all_chap_refs = re.findall(r'chapter-([\d\.]+)', html)
    all_chap_nums = sorted(list(set(float(x) for x in all_chap_refs)))
    print("All chapter numbers in HTML:", all_chap_nums)
except Exception as e:
    print("Error:", e)
