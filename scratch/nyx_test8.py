import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    # See all /series/romance-starting-with-parenting/ links
    links = re.findall(r'href=[\'"](/series/romance-starting-with-parenting[^\'"]*)[\'"]', html)
    unique_links = set(links)
    print(f"Total unique links to series: {len(unique_links)}")
    
    chapter_links = [l for l in unique_links if 'chapter' in l]
    print(f"Total chapter links: {len(chapter_links)}")
    
    # Let's see if there is a pagination API or something like that
    api_calls = re.findall(r'(/api/[^\'"]+)', html)
    print("API Calls found:", set(api_calls))
    
    # Look for any JSON-like data that might contain all chapters
    import json
    # NextJS app router might use self.__next_f
    next_f_matches = re.findall(r'self\.__next_f\.push\(\[(.*?)\)\]\)', html)
    for m in next_f_matches:
        if 'chapter' in m:
            print("Found chapter data in next_f!")
except Exception as e:
    print("Error:", e)
