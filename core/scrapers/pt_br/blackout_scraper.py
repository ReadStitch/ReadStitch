import logging
import json
import urllib.request
import re
from typing import List, Dict, Any, Optional
from ..base_scraper import BaseScraper
from core.cloudflare_bypass import get_cookie_header, save_cookies, load_saved_cookies

logger = logging.getLogger(__name__)

class BlackoutComicsScraper(BaseScraper):
    """
    Scraper para o site Blackout Comics.
    Requer login obrigatório para acesso aos capítulos.
    Utiliza Playwright para automatizar o login e burlar o Cloudflare.
    """
    
    @property
    def name(self):
        return "Blackout Comics"

    def __init__(self):
        super().__init__()
        self.base_url = "https://blackoutcomics.com"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': f"{self.base_url}/"
        })
        self.cookies_loaded = False
        self._load_cookies()

    def _load_cookies(self):
        cookie_header = get_cookie_header("blackoutcomics.com")
        if cookie_header:
            self.headers['Cookie'] = cookie_header
            self.cookies_loaded = True

    def login(self, email, password):
        # O login agora é feito manualmente pelo usuário no navegador embutido (botão Cloudflare)
        pass

    def has_active_login(self):
        return 'blackout_session' in self.headers.get('Cookie', '') or 'remember_web_' in self.headers.get('Cookie', '')

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        html = self._fetch_html(series_url)
        
        # Verifica se pediu login modal (usuário não logado)
        if "showLoginModal()" in html or not self.has_active_login():
            raise Exception(
                "Necessário fazer login. Clique no botão '🛡 Resolver Proteção Cloudflare', "
                "faça login com sua conta no site, e feche a janela quando terminar para salvar a sessão."
            )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Procura os capítulos
        # Normalmente div.flex.flex-col > a href="/comics/ID/capitulo-X"
        chapters = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Se for link de capítulo
            if '/comics/' in href and '/capitulo-' in href:
                url = href if href.startswith('http') else f"{self.base_url}{href}"
                if url not in chapters:
                    chapters.append(url)
                    
        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")
            
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        html = self._fetch_html(chapter_url)
        
        # Verifica se pediu login modal (usuário não logado)
        if "showLoginModal()" in html or not self.has_active_login():
            raise Exception(
                "Necessário fazer login. Clique no botão '🛡 Resolver Proteção Cloudflare', "
                "faça login com sua conta no site, e feche a janela quando terminar para salvar a sessão."
            )
            
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # As imagens do Blackout geralmente estão em um #pages div ou como lista na estrutura do site
        # Vamos procurar div > img que contenha src vindo do CDN deles
        images = []
        
        # A página de leitura carrega um alpine x-data com um array de urls de imagem
        # Geralmente em scripts locais ou attributes
        script_matches = re.findall(r'images:\s*(\[[^\]]+\])', html)
        if not script_matches:
            # Tenta também o S = [...] como usado pelo Tachiyomi
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
                
        if not images:
            # Fallback para imgs normais
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and ('/storage/' in src or '/media/' in src or '/pages/' in src):
                    if src not in images:
                        images.append(src if src.startswith('http') else f"{self.base_url}{src}")
                        
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis ou o site bloqueou o acesso.")
            
        return images
