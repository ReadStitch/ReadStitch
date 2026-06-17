import logging
import urllib.request
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class HipercoolScraper(BaseScraper):
    """Scraper para o site Hipercool (Madara base)."""
    
    @property
    def name(self):
        return "Hipercool"

    def __init__(self):
        super().__init__()
        self.headers.update({
            'Referer': 'https://hiper.cool/'
        })

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Tenta pegar os capítulos diretamente do DOM (Madara atualizado)
        chapters = []
        for item in soup.select('.wp-manga-chapter a'):
            href = item.get('href')
            if href:
                chapters.append(href)
                
        if not chapters:
            logger.warning(f"[{self.name}] Não encontrou capítulos no DOM, tentando POST via AJAX...")
            try:
                # Tenta o método POST ajax se não encontrou no DOM (Madara clássico)
                ajax_url = series_url.rstrip('/') + "/ajax/chapters/"
                req = urllib.request.Request(ajax_url, headers=self.headers, method="POST")
                with urllib.request.urlopen(req) as response:
                    ajax_html = response.read().decode('utf-8', errors='ignore')
                    soup_ajax = BeautifulSoup(ajax_html, 'html.parser')
                    for item in soup_ajax.select('.wp-manga-chapter a'):
                        href = item.get('href')
                        if href:
                            chapters.append(href)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao buscar via AJAX: {e}")
                
        if not chapters:
            raise Exception("Não foi possível encontrar a lista de capítulos")
            
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        html = self._fetch_html(chapter_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        images = []
        for img in soup.select('.reading-content img'):
            # Madara costuma colocar a imagem real em src, data-src ou data-lazy-src
            src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
            if src:
                images.append(src.strip())
                
        if not images:
            logger.error(f"[{self.name}] Nenhuma imagem extraída")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
