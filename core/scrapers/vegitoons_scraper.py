import logging
import urllib.request
import json
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class VegitoonsScraper(BaseScraper):
    """Scraper para o site Vegitoons."""
    
    @property
    def name(self):
        return "Vegitoons"

    def __init__(self):
        super().__init__()
        self.base_url = "https://vegitoons.black"
        self.api_url = "https://api.vegitoons.black"
        self.cdn_url = "https://api.vegitoons.black/cdn"
        self.headers.update({
            'Accept': 'application/json',
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
            'scan-id': '1'
        })

    def _fetch_api(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8', errors='ignore')
            return json.loads(data)

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        # Extrai o ID (ou slug) da URL da série
        # Ex: https://vegitoons.black/obra/10946/a-101-heroina
        parts = [p for p in series_url.split('?')[0].split('/') if p]
        
        try:
            # O ID geralmente vem logo após /obra/
            obra_idx = parts.index('obra')
            obra_id = parts[obra_idx + 1]
            
            # Pega os detalhes da obra na API
            details_url = f"{self.api_url}/obras/{obra_id}"
            details_data = self._fetch_api(details_url)
            
            chapters_data = details_data.get('capitulos', [])
            
            if not chapters_data:
                logger.warning(f"[{self.name}] Nenhum capítulo encontrado para a obra {obra_id}")
                return []
                
            all_chapters = []
            for item in chapters_data:
                chap_id = item.get('cap_id')
                chap_num = item.get('cap_numero')
                
                if chap_id and chap_num is not None:
                    # Usamos a URL fake com o chap_num para o gui ler bonito e passamos o ID no fragmento
                    url = f"{self.base_url}/capitulo-{chap_num}#chapterId={chap_id}"
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
            
            api_chap_url = f"{self.api_url}/capitulos/{chapter_id}"
            chap_data = self._fetch_api(api_chap_url)
            
            pages = chap_data.get('cap_paginas', [])
            if not pages:
                raise Exception("O capítulo não possui imagens acessíveis")
                
            images = []
            for p in pages:
                img_path = p.get('path')
                if img_path:
                    images.append(f"{self.cdn_url}/{img_path.lstrip('/')}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
