import logging
import urllib.request
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PlumaComicsScraper(BaseScraper):
    """Scraper para o site Pluma Comics."""
    
    def __init__(self):
        super().__init__()
        self.headers['Referer'] = 'https://plumacomics.cloud/'
        self.headers['Origin'] = 'https://plumacomics.cloud'

    @property
    def name(self):
        return "Pluma Comics"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        chapters = []
        # O Tachiyomi seleciona links dentro de .card que contenham ler ou agora /view/
        for a in soup.select('a[href*="/view/"]'):
            href = a.get('href')
            if not href:
                continue
                
            # Extrair o nome do capítulo
            span = a.find('span')
            title = span.get_text(strip=True) if span else a.get_text(strip=True)
            
            title_lower = title.lower()
            if "começar" in title_lower or "último" in title_lower or "leitura" in title_lower:
                continue
            
            # Monta a URL absoluta com o título como âncora para a GUI usar no nome do capítulo
            url = urljoin("https://plumacomics.cloud", href)
            if title:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', title)
                if match:
                    url = f"{url}#capitulo-{match.group(1)}"
                else:
                    title_clean = title.replace(' ', '-').replace('\n', '')
                    url = f"{url}#{title_clean}"
                
            chapters.append(url)
            
        # Deduplicar preservando a ordem
        seen = set()
        ordered_chapters = []
        for ch in chapters:
            if ch not in seen:
                seen.add(ch)
                ordered_chapters.append(ch)
                
        if not ordered_chapters:
            logger.error(f"[{self.name}] Nenhum capítulo encontrado")
            raise Exception("Não foi possível encontrar a lista de capítulos")
            
        logger.info(f"[{self.name}] Encontrados {len(ordered_chapters)} capítulos")
        return ordered_chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        try:
            # A url do capítulo deve ignorar a âncora para buscar o HTML real
            clean_url = chapter_url.split('#')[0]
            html = self._fetch_html(clean_url)
            soup = BeautifulSoup(html, 'html.parser')
            
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                # Procura por imagens de capítulos e ignora ícones/logos/capas
                if src and ('cdn.' in src or '/chapters/' in src or '/cap-' in src) and not any(x in src.lower() for x in ['logo', 'icon', 'cover', 'branding', 'banner']):
                    images.append(src)
                    
            if not images:
                logger.error(f"[{self.name}] Nenhuma imagem encontrada no HTML")
                raise Exception("O capítulo não possui imagens acessíveis")
                
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar imagens do capítulo: {e}")
            raise Exception(f"Falha ao obter dados do capítulo: {e}")
