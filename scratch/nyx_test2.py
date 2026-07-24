import urllib.request
import re

url = 'https://nyxscans.com/series/romance-starting-with-parenting/chapter-1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    # Try finding typical NextJS or image arrays
    
    # Try finding __NEXT_DATA__
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
    if match:
        print("NEXT_DATA found!")
        
    # Try finding tsReader or similar objects
    match2 = re.search(r'ts_reader\.run\((.*?)\);', html)
    if match2:
        print("ts_reader found!")
        
    # Look for img tags
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    imgs = soup.find_all('img')
    print(f"Total img tags: {len(imgs)}")
    for img in imgs:
        src = img.get('src')
        if src and ('chapter' in src or 'uploads' in src or 'media' in src):
            print(src)
            
except Exception as e:
    print("Error:", e)
