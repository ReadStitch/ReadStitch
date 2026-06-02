import logging
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from urllib.error import HTTPError
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ResetScansScraper(BaseScraper):
    @property
    def name(self):
        return "ResetScans"

    def __init__(self):
        super().__init__()
        self.headers.update({
            'Referer': 'https://reset-scans.org/'
        })

    def _fetch_html(self, url, method="GET", data=None):
        req_data = None
        if data:
            req_data = urllib.parse.urlencode(data).encode('utf-8')
            
        req = urllib.request.Request(url, data=req_data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8', errors='ignore')
        except HTTPError as e:
            if e.code in (403, 503):
                # Tenta fallback para cloudscraper se o Cloudflare estiver ativo
                try:
                    import cloudscraper
                    scraper = cloudscraper.create_scraper()
                    if method == "POST":
                        res = scraper.post(url, data=data, headers=self.headers)
                    else:
                        res = scraper.get(url, headers=self.headers)
                    if res.status_code == 200:
                        return res.text
                except Exception:
                    pass
            raise e

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        chapters = []
        
        # Madara clássico: tenta pegar da página inicial direto
        for item in soup.select('li.wp-manga-chapter a'):
            href = item.get('href')
            if href:
                chapters.append(href)
                
        if not chapters:
            logger.info(f"[{self.name}] Não encontrou capítulos no DOM, tentando POST via admin-ajax.php...")
            
            # Pega o ID do mangá da página
            manga_id = None
            rating_input = soup.find('input', class_='rating-post-id')
            if rating_input:
                manga_id = rating_input.get('value')
            else:
                chapters_holder = soup.find(id='manga-chapters-holder')
                if chapters_holder:
                    manga_id = chapters_holder.get('data-id')
                    
            if manga_id:
                try:
                    ajax_url = "https://reset-scans.org/wp-admin/admin-ajax.php"
                    post_data = {
                        "action": "manga_get_chapters",
                        "manga": manga_id
                    }
                    
                    ajax_html = self._fetch_html(ajax_url, method="POST", data=post_data)
                    soup_ajax = BeautifulSoup(ajax_html, 'html.parser')
                    for item in soup_ajax.select('li.wp-manga-chapter a'):
                        href = item.get('href')
                        if href:
                            chapters.append(href)
                except Exception as e:
                    logger.error(f"[{self.name}] Erro ao buscar via AJAX: {e}")
            else:
                logger.error(f"[{self.name}] manga_id não encontrado na página!")
                
        if not chapters:
            raise Exception("Não foi possível encontrar a lista de capítulos (Madara endpoint falhou).")
            
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        # Inverte pois o Madara retorna do mais recente para o mais antigo, e o leitor costuma querer na ordem normal
        return list(reversed(chapters))

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        html = self._fetch_html(chapter_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        images = []
        for img in soup.select('.reading-content img'):
            # Madara costuma colocar a imagem real nestes atributos para lazy loading
            src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
            if src:
                images.append(src.strip())
                
        if not images:
            logger.error(f"[{self.name}] Nenhuma imagem extraída")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
