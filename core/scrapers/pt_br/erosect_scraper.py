import logging
import urllib.request
import re
import urllib.parse
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper
from core.cloudflare_bypass import get_cookie_header

logger = logging.getLogger(__name__)

class ErosectScraper(BaseScraper):
    """
    Scraper para o site Erosect.
    Requer login obrigatório e resolução do Cloudflare.
    """
    
    @property
    def name(self):
        return "Erosect"

    def __init__(self):
        super().__init__()
        self.base_url = "https://erosect.xyz"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': f"{self.base_url}/"
        })
        self.cookies_loaded = False
        self._load_cookies()

    def _load_cookies(self):
        cookie_header = get_cookie_header("erosect.xyz")
        if cookie_header:
            self.headers['Cookie'] = cookie_header
            self.cookies_loaded = True

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        try:
            html = self._fetch_html(series_url)
        except urllib.error.HTTPError as e:
            if e.code in (403, 401):
                raise Exception(
                    "Acesso negado (Cloudflare ou Login). Clique no botão '🛡 Resolver Proteção Cloudflare', "
                    "faça login em https://erosect.xyz/login e feche a janela quando terminar para salvar a sessão."
                )
            raise e
        except Exception as e:
            raise e
            
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        
        # Procura por links de capítulos
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Critérios comuns de capítulos
            if ('/capitulo' in href.lower() or '/ler/' in href.lower() or '/chapter' in href.lower() or '/episodio' in href.lower() or '-capitulo-' in href.lower()):
                url = href if href.startswith('http') else f"{self.base_url}{href}"
                if url not in chapters:
                    chapters.append(url)
                    
        # Fallback: links que derivam da URL principal mas são mais longos (provavelmente capítulos)
        if not chapters:
            base_path = urllib.parse.urlparse(series_url).path
            if base_path.endswith('/'):
                base_path = base_path[:-1]
                
            for a in soup.find_all('a', href=True):
                href = a['href']
                if base_path in href and href != base_path and href != base_path + '/':
                    url = href if href.startswith('http') else f"{self.base_url}{href}"
                    if url not in chapters:
                        chapters.append(url)

        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")
            
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens em: {chapter_url}")
        try:
            html = self._fetch_html(chapter_url)
        except urllib.error.HTTPError as e:
            if e.code in (403, 401):
                raise Exception(
                    "Acesso negado (Cloudflare ou Login). Clique no botão '🛡 Resolver Proteção Cloudflare', "
                    "faça login em https://erosect.xyz/login e feche a janela quando terminar para salvar a sessão."
                )
            raise e
        except Exception as e:
            raise e
            
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        # Tenta achar arrays JS como em alguns sites (alpine x-data ou scripts do tachiyomi)
        script_matches = re.findall(r'images:\s*(\[[^\]]+\])', html)
        if not script_matches:
            script_matches = re.findall(r'S\s*=\s*(\[[\s\S]*?\])', html)
            
        if script_matches:
            try:
                import ast
                images_list = ast.literal_eval(script_matches[0])
                for img in images_list:
                    if isinstance(img, str):
                        images.append(img if img.startswith('http') else f"{self.base_url}{img}")
            except Exception:
                pass
                
        # Fallback para tags de imagem no HTML
        if not images:
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src:
                    src = src.strip()
                    # Ignorar imagens de interface comum
                    lower_src = src.lower()
                    if any(x in lower_src for x in ['avatar', 'logo', 'banner', 'icon', 'pixel', 'discord']):
                        continue
                    if src not in images:
                        images.append(src if src.startswith('http') else f"{self.base_url}{src}")
                        
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis ou o site bloqueou o acesso.")
            
        return images
