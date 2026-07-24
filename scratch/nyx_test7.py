import urllib.request
from bs4 import BeautifulSoup

url = 'https://nyxscans.com/series/romance-starting-with-parenting/chapter-28'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

soup = BeautifulSoup(html, 'html.parser')
imgs = soup.find_all('img')
for img in imgs:
    src = img.get('src') or ''
    if '/upload/' in src:
        parent_class = img.parent.get('class', []) if img.parent else []
        print(f"SRC: {src[:60]} | CLASS: {img.get('class')} | PARENTS: {parent_class}")
