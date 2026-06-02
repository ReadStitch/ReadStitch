import logging
import urllib.request
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GenzScraper(BaseScraper):
    """Scraper para o site GenzToons."""

    @property
    def name(self):
        return "GenzToons"

    def __init__(self):
        super().__init__()
        self.base_url = "https://genztoons.org"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/"
        })
        self.cdn_domain = "https://cdn.meowing.org"

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        try:
            req = urllib.request.Request(series_url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
            soup = BeautifulSoup(html, 'html.parser')
            
            all_chapters = []
            links = soup.find_all('a')
            for a in links:
                href = a.get('href', '')
                if '/chapter/' in href:
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = self.base_url + href
                        else:
                            href = self.base_url + '/' + href
                    
                    # Tenta extrair o número do capítulo do title ou alt do elemento <a>
                    title = a.get('title', '') or a.get('alt', '')
                    if title:
                        m = re.search(r'Chapter\s*([\d.]+)', title, re.IGNORECASE)
                        if m:
                            chapter_number = m.group(1)
                            href = f"{href}?chapter={chapter_number}"
                    
                    if href not in all_chapters:
                        # Se já existe uma versão com esse mesmo path, ignorar
                        path_only = href.split('?')[0]
                        if not any(existing.startswith(path_only) for existing in all_chapters):
                            all_chapters.append(href)
            
            # Sort manually if they are reversed or let GUI handle it. 
            # Reversing usually helps if chapter 1 is last in the DOM.
            all_chapters.reverse()
            
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception(f"Falha ao obter a lista de capítulos: {e}")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens em: {chapter_url}")
        
        try:
            req = urllib.request.Request(chapter_url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check for dynamic CDN domain in the HTML if possible
            cdn_match = re.search(r'(https://cdn\.[a-zA-Z0-9.-]+)/uploads', html)
            if cdn_match:
                current_cdn = cdn_match.group(1)
            else:
                current_cdn = self.cdn_domain
                
            images = []
            imgs = soup.find_all('img')
            for img in imgs:
                uid = img.get('uid')
                if uid:
                    img_url = f"{current_cdn}/uploads/{uid}"
                    if img_url not in images:
                        images.append(img_url)
                        
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens (UIDs)")
            
            if not images:
                logger.warning(f"[{self.name}] Nenhuma imagem (UID) encontrada. Pode ser um capítulo pago/locked.")
                
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception(f"Falha ao obter imagens do capítulo: {e}")
