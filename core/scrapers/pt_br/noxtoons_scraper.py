import urllib.request
import re
import logging
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class NoxToonsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://noxtoons.com"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/"
        })

    @property
    def name(self):
        return "NoxToons"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        chapters = []
        # As URLs de capítulos estão no formato /ler/<slug-do-manga>/capitulo-<numero>
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/ler/') and ('capitulo' in href or 'chapter' in href):
                full_url = f"{self.base_url}{href}" if href.startswith('/') else href
                if full_url not in chapters:
                    chapters.append(full_url)
                    
        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")

        # Ordenar (decrescente, geralmente vem invertido, mas vamos ordenar crescente se não estiver)
        # O padrão pode ser ler da web e extrair o número
        sorted_chapters = []
        for url in chapters:
            match = re.search(r'(?:capitulo|chapter)[-]?([\d.]+)', url, re.IGNORECASE)
            if match:
                num = float(match.group(1))
                sorted_chapters.append((num, url))
            else:
                sorted_chapters.append((0.0, url))
                
        sorted_chapters.sort(key=lambda x: x[0])
        return [c[1] for c in sorted_chapters]

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens do capítulo em: {chapter_url}")
        
        html = self._fetch_html(chapter_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        images = []
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and ('/chapters/' in src or '/uploads/' in src):
                full_src = src
                if src.startswith('/'):
                    full_src = f"{self.base_url}{src}"
                elif not src.startswith('http'):
                    continue # Ignorar imagens relativas estranhas se não começam com /

                if full_src not in images:
                    images.append(full_src)
                    
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis.")
            
        return images
