import json
import logging
import urllib.request
import urllib.parse
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GeassComicsScraper(BaseScraper):
    """Scraper para o site Geass Comics."""
    
    @property
    def name(self):
        return "Geass Comics"

    def __init__(self):
        super().__init__()
        self.base_url = "https://geasscomics.xyz"
        self.api_url = "https://api.geasscomics.xyz"
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
        try:
            req = urllib.request.Request(series_url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            import re
            # Extrai hrefs de capítulos do HTML renderizado pelo Next.js
            # Ex: \"href\":\"/read/criador-de-lendas-urbanas/1\"
            chapters_paths = re.findall(r'\\"href\\":\\"(/read/[^/]+/[0-9.]+)\\"', html)
            
            if not chapters_paths:
                # Fallback, tenta procurar por /obra/ caso mude
                chapters_paths = re.findall(r'\\"href\\":\\"(/obra/[^/]+/[0-9.]+)\\"', html)
                
            if not chapters_paths:
                logger.warning(f"[{self.name}] Nenhum capítulo encontrado.")
                return []
                
            # Remove duplicatas
            chapters_paths = list(set(chapters_paths))
            
            def get_num(path):
                try:
                    return float(path.split('/')[-1])
                except:
                    return 0
                    
            # Ordena decrescente (do mais novo pro mais antigo, como padrão)
            chapters_paths = sorted(chapters_paths, key=get_num, reverse=True)
            
            all_chapters = [f"{self.base_url}{path}" for path in chapters_paths]
            
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception("Falha ao obter a lista de capítulos")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        try:
            req = urllib.request.Request(chapter_url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            import re
            import json
            
            # Extrai o array JSON de páginas injetado no HTML
            m = re.search(r'\\"pages\\":(\[.*?\])', html)
            if not m:
                raise Exception("Não foi possível encontrar as imagens na página do capítulo.")
                
            pages_str = m.group(1).replace('\\"', '"')
            images_list = json.loads(pages_str)
            
            images = []
            for img in images_list:
                if img.startswith('http'):
                    images.append(img)
                elif img.startswith('//'):
                    images.append(f"https:{img}")
                else:
                    images.append(f"https://cdn.geasscomics.xyz{img}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
