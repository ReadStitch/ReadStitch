import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
import logging
from core.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class HanamiHeavenScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Hanami Heaven"
        self.base_url = "https://hanamiheaven.org"
        self._headers = self.headers

    def get_chapters(self, series_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        if not series_url.endswith('/'):
            series_url += '/'
        
        # Madara utiliza ajax/chapters/ via POST para recuperar a lista em formato HTML
        ajax_url = series_url + 'ajax/chapters/'
        req = urllib.request.Request(ajax_url, method='POST', headers=self._headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            chapters = []
            seen = set()
            
            # Encontrar todos os itens da lista wp-manga-chapter e extrair o link
            for item in soup.select('li.wp-manga-chapter a'):
                href = item.get('href')
                if href and href != '#' and href not in seen:
                    chapters.append(href)
                    seen.add(href)
                    
            logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
            return chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar capítulos: {e}")
            return []

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching images for chapter: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            # Imagens costumam ficar na div reading-content
            img_tags = soup.select('.reading-content img')
            for img in img_tags:
                src = img.get('data-src') or img.get('src')
                if src:
                    images.append(src.strip())
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens no capítulo.")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar página do capítulo: {e}")
            return []
