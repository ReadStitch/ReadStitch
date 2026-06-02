import os
import urllib.request
import urllib.parse
import re
from .base_scraper import BaseScraper

class VortexScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    @property
    def name(self) -> str:
        return "Vortex Scans"
        
    def _fetch_html(self, url: str) -> str:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
            
    def get_chapters(self, series_url: str) -> list[str]:
        if "/chapter" in series_url:
            return [series_url]
            
        html = self._fetch_html(series_url)
        
        slug = [p for p in series_url.strip('/').split('/') if p][-1]
        pattern = r'href=[\'\"](/series/' + re.escape(slug) + r'/(?:chapter|ch)-?[0-9\.]+)[\'\"]'
        
        # also match /series/slug/chapter-1 directly without checking the slug just in case
        pattern2 = r'href=[\'\"](/series/[^\'\"]+/(?:chapter|ch)-?[0-9\.]+)[\'\"]'
        
        links = re.findall(pattern2, html)
        domain = "hivetoons.org" if "hivetoons.org" in series_url else "vortexscans.org"
        
        chapters = set()
        for href in links:
            if slug in href:
                full_url = f"https://{domain}{href}" if href.startswith('/') else href
                chapters.add(full_url)
                
        def get_chap_num(url):
            try:
                # Extracts the number from strings like chapter-1.5 or ch-2
                match = re.search(r'(?:chapter|ch)-?([0-9\.]+)', url)
                return float(match.group(1)) if match else 0
            except:
                return 0
                
        return sorted(list(chapters), key=get_chap_num, reverse=True)

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        html = self._fetch_html(chapter_url)
        
        # Vortex/Hivetoons usa tags do tipo <meta itemprop="image" content="...">
        images = re.findall(r'<meta itemprop=[\'\"]image[\'\"] content=[\'\"](https://[^\'\"]+(?:jpg|jpeg|png|webp))[\'\"]', html)
        
        if not images:
            # Fallback para imgs genéricas caso mudem o HTML
            images = re.findall(r'src=[\'\"](https://storage\.[^\'\"]+(?:jpg|jpeg|png|webp))[\'\"]', html)
            
        if not images:
            raise Exception("Nenhuma imagem encontrada no capítulo Vortex.")
            
        ordered = []
        seen = set()
        for img_url in images:
            if img_url not in seen:
                seen.add(img_url)
                ordered.append(img_url)
                
        return ordered
