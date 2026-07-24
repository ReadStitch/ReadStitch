import urllib.request
from bs4 import BeautifulSoup

url = 'https://nyxscans.com/series/romance-starting-with-parenting/chapter-1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

soup = BeautifulSoup(html, 'html.parser')
imgs = soup.find_all('img')
for img in imgs:
    src = img.get('src') or ''
    if '/upload/' in src and not img.get('class'):
        # Check parents to find a common container class
        parents = [p.name + ('.' + '.'.join(p.get('class', [])) if p.get('class') else '') for p in img.parents][:3]
        print(f"SRC: {src[:40]} | PARENTS: {parents}")
