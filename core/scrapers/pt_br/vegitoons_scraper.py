import logging
import urllib.request
import json
from ..base_scraper import BaseScraper

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
        self.cdn_url = "https://cdn.vegitoons.black"
        self.cdn_api_url = "https://api.vegitoons.black/cdn"
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
            obra_id = None
            if 'obra' in parts:
                obra_id = parts[parts.index('obra') + 1]
            elif 'obras' in parts:
                obra_id = parts[parts.index('obras') + 1]
            else:
                nums = [p for p in parts if p.isdigit()]
                if nums:
                    obra_id = nums[0]
                else:
                    raise Exception("URL inválida ou ID da obra não encontrado.")
            
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
                
            obra_dict = chap_data.get('obra') or {}
            scan_id = obra_dict.get('scan_id', 1)
            obr_id = chap_data.get('obr_id') or obra_dict.get('obr_id')
            cap_numero = chap_data.get('cap_numero')
            is_wp = chap_data.get('is_wp', False)
                
            images = []
            for p in pages:
                if isinstance(p, str):
                    if p.startswith('http'):
                        images.append(p)
                    elif p.startswith('/'):
                        images.append(f"{self.cdn_url}{p}")
                    continue
                    
                img_src = p.get('src') or p.get('path')
                if img_src:
                    if is_wp:
                        images.append(f"{self.cdn_url}/wp-content/uploads/WP-manga/data/{img_src.lstrip('/')}")
                    else:
                        images.append(f"{self.cdn_url}/scans/{scan_id}/obras/{obr_id}/capitulos/{cap_numero}/{img_src.lstrip('/')}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
