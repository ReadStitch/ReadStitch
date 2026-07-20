import logging
import urllib.request
import urllib.error
import json
import re
from ..base_scraper import BaseScraper
from core.cloudflare_bypass import get_cookie_header

logger = logging.getLogger(__name__)

class LycanToonsScraper(BaseScraper):
    """Scraper para o site LycanToons."""
    
    def __init__(self):
        super().__init__()
        self._load_cookies()

    def _load_cookies(self):
        cookie_header = get_cookie_header("lycantoons.com")
        if cookie_header:
            self.headers['Cookie'] = cookie_header

    @property
    def name(self):
        return "Lycan Toons"

    def _fetch_api(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403, 503):
                raise Exception("Acesso bloqueado (Cloudflare). Clique no botão '🛡 Resolver Proteção Cloudflare', aguarde a verificação e tente novamente.")
            raise e
        except Exception as e:
            if '403' in str(e) or '503' in str(e):
                raise Exception("Acesso bloqueado (Cloudflare). Clique no botão '🛡 Resolver Proteção Cloudflare', aguarde a verificação e tente novamente.")
            raise e

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        # Extrair o slug da série da URL
        slug = series_url.strip('/').split('/')[-1]
        api_url = f"https://lycantoons.com/api/series/{slug}"
        
        try:
            resp = self._fetch_api(api_url)
            data = json.loads(resp)
        except Exception as e:
            if "Cloudflare" in str(e):
                raise e
            logger.error(f"[{self.name}] Erro ao buscar dados da série: {e}")
            raise Exception("Não foi possível acessar a API do Lycan Toons")
            
        chapters_data = data.get('capitulos', [])
        if not chapters_data:
            raise Exception("Não foi possível encontrar a lista de capítulos")
            
        # O LycanToons costuma retornar em ordem mais recente para mais antiga,
        # Tachiyomi faz .sortedByDescending { it.chapter_number }.
        # O python default sort com uma função deve funcionar, 
        # mas vamos tentar manter a ordem se já estiver decrescente, senão reordenamos.
        try:
            chapters_data = sorted(chapters_data, key=lambda x: float(x.get('numero', 0)), reverse=True)
        except Exception:
            pass
        
        chapters = []
        for chap in chapters_data:
            chap_slug = chap.get('slug') or str(chap.get('numero'))
            url = f"https://lycantoons.com/series/{slug}/{chap_slug}"
            
            title = chap.get('titulo') or chap.get('title')
            chap_num = chap.get('numero')
            
            # Adicionar âncora para formatar bonito no GUI
            if title:
                match = re.search(r'(\d+(?:\.\d+)?)', title)
                if match:
                    url = f"{url}#capitulo-{match.group(1)}"
                else:
                    title_clean = title.replace(' ', '-').replace('\n', '')
                    url = f"{url}#{title_clean}"
            elif chap_num is not None:
                url = f"{url}#capitulo-{chap_num}"
                
            chapters.append(url)
            
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        # Limpar âncoras da URL
        clean_url = chapter_url.split('#')[0]
        
        try:
            html = self._fetch_api(clean_url)
        except Exception as e:
            if "Cloudflare" in str(e):
                raise e
            logger.error(f"[{self.name}] Erro ao buscar página do capítulo: {e}")
            raise Exception("Falha ao obter página do capítulo")
            
        # Buscar "imageUrls": [ ... ] no código fonte (Next.js data/QuickJS na Tachiyomi)
        # Como o JSON pode estar escapado dentro do HTML, procuramos a ocorrência com ou sem escape
        match = re.search(r'\\?"imageUrls\\?":\s*(\[.*?\])', html)
        if not match:
            logger.error(f"[{self.name}] Não foi possível encontrar imageUrls no HTML")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        try:
            # Remove escapes se houver para tornar o JSON válido
            json_str = match.group(1).replace('\\"', '"')
            images = json.loads(json_str)
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao parsear imageUrls JSON: {e}")
            raise Exception("Falha ao processar imagens do capítulo")
            
        if not images:
            raise Exception("Nenhuma imagem extraída")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
