import json
import logging
import urllib.request
import urllib.parse
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GeassComicsScraper(BaseScraper):
    """Scraper para o site Geass Comics."""
    
    @property
    def name(self):
        return "Geass Comics"

    def __init__(self):
        super().__init__()
        self.base_url = "https://geasscomics.xyz"
        self.api_url = "https://api.skkyscan.fun"
        self.headers.update({
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
            'Accept': 'application/json, text/plain, */*'
        })

    def _fetch_json(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        # Extrai o slug da URL da série
        # Ex: https://geasscomics.xyz/obra/nome-da-obra
        parts = [p for p in series_url.split('?')[0].split('/') if p]
        slug = parts[-1]
        
        try:
            # 1. Pega os detalhes do mangá para obter o ID
            details_url = f"{self.api_url}/api/mangas/{slug}"
            details_data = self._fetch_json(details_url)
            manga_id = details_data.get('data', {}).get('id')
            
            if not manga_id:
                raise Exception("Manga ID não encontrado na resposta.")
                
            # 2. Pega a lista de capítulos usando paginação
            all_chapters = []
            current_page = 1
            has_more = True
            
            while has_more:
                chapters_url = f"{self.api_url}/api/chapters?mangaId={manga_id}&page={current_page}&limit=100&order=desc"
                chapters_data = self._fetch_json(chapters_url)
                
                items = chapters_data.get('data', [])
                for item in items:
                    chap_num = item.get('chapterNumber')
                    chap_id = item.get('id')
                    
                    if chap_num is not None and chap_id:
                        # Precisamos salvar o chapter ID na URL para poder pegar as imagens depois
                        url = f"{self.base_url}/ler/{slug}/{chap_num}#chapterId={chap_id}"
                        all_chapters.append(url)
                
                pagination = chapters_data.get('pagination', {})
                # Checa se há próxima página comparando a página atual com o total
                has_more = current_page < pagination.get('totalPages', 1)
                current_page += 1
                
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception("Falha ao obter a lista de capítulos")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        try:
            # Extrai o chapterId que colocamos no final da URL
            if '#chapterId=' not in chapter_url:
                raise Exception("Chapter ID ausente na URL")
                
            chapter_id = chapter_url.split('#chapterId=')[1]
            
            # Chama a API do capítulo para obter as imagens
            api_chap_url = f"{self.api_url}/api/chapters/{chapter_id}"
            chap_data = self._fetch_json(api_chap_url)
            
            pages = chap_data.get('data', {}).get('pages', [])
            if not pages:
                raise Exception("O capítulo não possui imagens acessíveis")
                
            # Ordena as páginas pelo pageNumber
            pages = sorted(pages, key=lambda x: x.get('pageNumber', 0))
            
            images = []
            for p in pages:
                img_path = p.get('imageUrl')
                if img_path:
                    # Se o img_path já vier com http, não concatena
                    if img_path.startswith('http'):
                        images.append(img_path)
                    else:
                        images.append(f"{self.api_url}{img_path}")
                        
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
