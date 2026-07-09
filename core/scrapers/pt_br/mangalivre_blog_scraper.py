import re
import urllib.request
from bs4 import BeautifulSoup
from typing import List
import logging
from core.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MangaLivreBlogScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Manga Livre Blog"
        self.base_url = "https://mangalivre.blog"

    def get_chapters(self, series_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        req = urllib.request.Request(series_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            chapters = []
            seen = set()
            
            for a in soup.select('a'):
                href = a.get('href')
                if href and 'capitulo' in href and href not in seen:
                    if '/capitulo/' in href:
                        chapters.append(href)
                        seen.add(href)
                    
            logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
            return chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar capítulos: {e}")
            return []

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching images for chapter: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            for img in soup.select('img'):
                src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
                if src and ('wp-content/uploads' in src) and 'flagcdn' not in src:
                    src = src.strip()
                    if src not in images:
                        images.append(src)
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens no capítulo.")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar página do capítulo: {e}")
            return []
