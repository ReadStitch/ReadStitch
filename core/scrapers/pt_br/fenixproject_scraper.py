import urllib.request
import urllib.parse
import re
import logging
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FenixProjectScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://fenixproject.site"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/"
        })

    @property
    def name(self):
        return "Fenix Project"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        # 1. Tentar pegar a ID do mangá a partir do HTML da página da série
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        manga_id = None
        manga_id_tag = soup.find('div', id='manga-chapters-holder')
        if manga_id_tag and manga_id_tag.get('data-id'):
            manga_id = manga_id_tag.get('data-id')
            
        if not manga_id:
            # Alternativa: procurar wp-manga-post-id
            manga_id_input = soup.find('input', class_='wp-manga-post-id')
            if manga_id_input:
                manga_id = manga_id_input.get('value')
                
        if not manga_id:
            # Tentar achar no script
            match = re.search(r'manga_id\s*=\s*["\'](\d+)["\']', html)
            if match:
                manga_id = match.group(1)

        chapters = []
        if manga_id:
            # 2. Fazer requisição POST para /ajax/chapters/ (novo padrão do Madara)
            ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"
            # Alguns usam ajax_url = series_url.rstrip('/') + '/ajax/chapters/'
            # Como a Fenix Project responde no /ajax/chapters/, vamos tentar ele primeiro
            ajax_chapters_url = series_url.rstrip('/') + '/ajax/chapters/'
            
            try:
                req = urllib.request.Request(ajax_chapters_url, method="POST", headers=self.headers)
                resp = urllib.request.urlopen(req).read().decode('utf-8')
                ajax_soup = BeautifulSoup(resp, 'html.parser')
                li_chapters = ajax_soup.find_all('li', class_='wp-manga-chapter')
                for li in li_chapters:
                    a_tag = li.find('a')
                    if a_tag:
                        chapters.append(a_tag['href'])
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao buscar capítulos via /ajax/chapters/: {e}")
                
            # Se não encontrou, tenta admin-ajax
            if not chapters:
                try:
                    data = urllib.parse.urlencode({
                        'action': 'manga_get_chapters',
                        'manga': manga_id
                    }).encode('utf-8')
                    req = urllib.request.Request(ajax_url, data=data, method="POST", headers=self.headers)
                    resp = urllib.request.urlopen(req).read().decode('utf-8')
                    ajax_soup = BeautifulSoup(resp, 'html.parser')
                    li_chapters = ajax_soup.find_all('li', class_='wp-manga-chapter')
                    for li in li_chapters:
                        a_tag = li.find('a')
                        if a_tag:
                            chapters.append(a_tag['href'])
                except Exception as e:
                    logger.warning(f"[{self.name}] Falha ao buscar capítulos via admin-ajax: {e}")

        # Se ainda não encontrou via ajax, tenta inline na página
        if not chapters:
            li_chapters = soup.find_all('li', class_='wp-manga-chapter')
            for li in li_chapters:
                a_tag = li.find('a')
                if a_tag:
                    chapters.append(a_tag['href'])

        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")
            
        # Garante URLs únicas mantendo a ordem
        unique_chapters = []
        for c in chapters:
            if c not in unique_chapters:
                unique_chapters.append(c)

        return unique_chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens do capítulo em: {chapter_url}")
        
        # A Fenix Project utiliza um plugin "wp-manga-chapter-images-protection" com AES CryptoJS
        # Para descriptografar a payload sem adicionar novas dependências complexas (pycryptodome) no ReadStitch,
        # vamos usar o Playwright para renderizar a página, executar o JS nativo de descriptografia e
        # interceptar as requisições que buscam as imagens no CDN (WP-manga/data).
        
        from playwright.sync_api import sync_playwright
        
        image_urls = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Intercepta as requisições para pescar os links das imagens
            def handle_request(req):
                # O padrão wp-content/uploads/WP-manga/data é padrão do Madara
                if 'WP-manga/data' in req.url or 'fenixproject.site/wp-content/uploads' in req.url:
                    # Filtra arquivos de imagem
                    if req.url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        # Ignora elementos de UI comuns do site
                        if not any(ui in req.url.lower() for ui in ['logo', 'background', 'cursor', 'avatar', '-75x106', '-32x32', 'seta']):
                            if req.url not in image_urls:
                                image_urls.append(req.url)
                                
            page.on("request", handle_request)
            
            try:
                # O site faz o decrypt logo ao carregar a página
                page.goto(chapter_url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                logger.warning(f"[{self.name}] Timeout ou erro no Playwright (ignorável se carregou imagens): {e}")

            browser.close()
            
        # O FenixProject coloca capas de scan em imgs como 00-site.webp ou 99-final.webp, as mantemos na ordem original que foram interceptadas
        # Como o intercept capturou na ordem de disparo, já deve estar correto.

        if not image_urls:
            raise Exception("Nenhuma imagem decodificada pelo Playwright foi encontrada para o capítulo.")

        return image_urls
