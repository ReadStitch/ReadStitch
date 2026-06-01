import logging
import urllib.request
from .base_scraper import BaseScraper
from .nexus_crypto import decrypt_response

logger = logging.getLogger(__name__)

class NexusScraper(BaseScraper):
    """Scraper para o site Nexus Toons."""
    
    @property
    def name(self):
        return "Nexus Toons"

    def __init__(self):
        super().__init__()
        self.base_url = "https://nx-toons.xyz"
        self.api_url = "https://nx-toons.xyz/api"
        self.headers.update({
            'Accept': 'application/json',
            'Referer': f"{self.base_url}/"
        })

    def _fetch_api(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8', errors='ignore')
            return decrypt_response(data)

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        # Extrai o slug da URL da série
        # Ex: https://nx-toons.xyz/manga/nome-da-obra
        parts = [p for p in series_url.split('?')[0].split('/') if p]
        slug = parts[-1]
        
        try:
            # Pega os detalhes do mangá
            details_url = f"{self.api_url}/manga/{slug}"
            details_data = self._fetch_api(details_url)
            
            if not details_data or 'chapters' not in details_data:
                raise Exception("Não foi possível carregar os capítulos (API retornou vazio)")
                
            chapters_data = details_data['chapters']
            
            all_chapters = []
            for item in chapters_data:
                chap_id = item.get('id')
                chap_num = item.get('number')
                
                if chap_id and chap_num is not None:
                    # Usamos a URL fake com o chap_num para o gui ler bonito e passamos o ID no fragmento
                    url = f"{self.base_url}/read/capitulo-{chap_num}#chapterId={chap_id}"
                    all_chapters.append(url)
                    
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception("Falha ao obter a lista de capítulos")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        try:
            if '#chapterId=' not in chapter_url:
                raise Exception("Chapter ID ausente na URL")
                
            chapter_id = chapter_url.split('#chapterId=')[1]
            
            api_chap_url = f"{self.api_url}/read/{chapter_id}"
            chap_data = self._fetch_api(api_chap_url)
            
            if not chap_data or 'pages' not in chap_data:
                raise Exception("O capítulo não possui imagens acessíveis")
                
            pages = chap_data['pages']
            page_token = chap_data.get('pageToken')
            
            images = []
            for index, p in enumerate(pages):
                img_url = p.get('imageUrl')
                if img_url:
                    images.append(img_url)
                elif page_token:
                    # Se não vier a URL diretamente, usa o pageToken + index
                    images.append(f"{self.api_url}/p/{page_token}/{index}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
