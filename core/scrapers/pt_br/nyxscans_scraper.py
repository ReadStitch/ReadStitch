import logging
import urllib.request
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class NyxScansScraper(BaseScraper):
    """Scraper para o site Nyx Scans."""
    
    @property
    def name(self):
        return "Nyx Scans"

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        req = urllib.request.Request(series_url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        parsed = urlparse(series_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        series_path = parsed.path.rstrip('/')
        series_slug = series_path.split('/')[-1]
        
        # 1. Busca links renderizados no HTML
        links = re.findall(r'href=[\'"](/series/[^\'"]+)[\'"]', html)
        
        # 2. Busca slugs ocultos no estado Next.js (paginação)
        slugs = re.findall(r'\\*"slug\\*":\\*"([^\\"]+)\\*"', html)
        
        chapters = []
        for link in links:
            if link != series_path and link not in chapters:
                chapters.append(link)
                
        for slug in slugs:
            if slug != series_slug:
                link = f"{series_path}/{slug}"
                if link not in chapters:
                    chapters.append(link)
                
        def get_chapter_num(link):
            match = re.search(r'chapter-([\d\.]+)', link)
            if match:
                return float(match.group(1))
            return 0.0

        chapters = sorted(chapters, key=get_chapter_num, reverse=True)
        
        return [f"{base_url}{link}" for link in chapters]

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        imgs = soup.find_all('img')
        
        images = []
        seen = set()
        
        for img in imgs:
            src = img.get('src')
            # As imagens reais do capítulo não possuem classes (são tags <img> limpas)
            # Imagens como banners, logos e recomendações possuem classes como 'object-cover', 'w-full', etc.
            if src and ('/upload/' in src) and not img.get('class'):
                if src not in seen:
                    if src.startswith('/'):
                        parsed = urlparse(chapter_url)
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                        src = f"{base_url}{src}"
                    seen.add(src)
                    images.append(src)
                    
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis ou a página está protegida.")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
