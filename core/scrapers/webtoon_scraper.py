import urllib.request
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class WebtoonScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers['Referer'] = 'https://www.webtoons.com'
        
    @property
    def name(self) -> str:
        return "Webtoons"

    def get_chapters(self, series_url: str) -> list[str]:
        if "episode_no=" in series_url:
            return [series_url]
            
        # Extract base URL and title_no
        base_url = series_url.split('?')[0]
        title_match = re.search(r'title_no=(\d+)', series_url)
        if not title_match:
            raise Exception("A URL do Webtoons deve conter o parâmetro title_no")
        title_no = title_match.group(1)
        
        all_chapters = set()
        page = 1
        
        while True:
            url = f"{base_url}?title_no={title_no}&page={page}"
            req = urllib.request.Request(url, headers=self.headers)
            try:
                html = urllib.request.urlopen(req).read().decode('utf-8')
            except Exception:
                break
                
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.find_all('li', class_='_episodeItem')
            
            if not items:
                break
                
            added = 0
            for item in items:
                a_tag = item.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    if href.startswith('http') and 'episode_no=' in href:
                        if href not in all_chapters:
                            all_chapters.add(href)
                            added += 1
                            
            if added == 0:
                break
            page += 1
            
        def get_chap_num(url):
            try:
                match = re.search(r'episode_no=(\d+(?:\.\d+)?)', url)
                return float(match.group(1)) if match else 0.0
            except:
                return 0
                
        return sorted(list(all_chapters), key=get_chap_num, reverse=True)

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            html = urllib.request.urlopen(req).read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Falha ao ler capítulo: {e}")
            
        soup = BeautifulSoup(html, 'html.parser')
        
        viewer = soup.find(id='_imageList')
        if not viewer:
            raise Exception("Nenhuma imagem encontrada no capítulo do Webtoon.")
            
        imgs = viewer.find_all('img')
        ordered = []
        for img in imgs:
            url = img.get('data-url')
            if url:
                ordered.append(url)
                
        return ordered
