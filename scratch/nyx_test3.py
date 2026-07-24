import sys
sys.path.append('f:/Projetos/programa/ReadStitch')
from core.scrapers.factory import get_scraper_for_url
scraper = get_scraper_for_url('https://nyxscans.com/series/romance-starting-with-parenting')
chapters = scraper.get_chapters('https://nyxscans.com/series/romance-starting-with-parenting')
print("First chapter:", chapters[0])
import urllib.request
req = urllib.request.Request(chapters[0], headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
imgs = soup.find_all('img')
print("Total imgs:", len(imgs))
for img in imgs:
    src = img.get('src')
    if src:
        print(src)
