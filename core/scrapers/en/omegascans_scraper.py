import urllib.request
import urllib.parse
import json
import re
from ..base_scraper import BaseScraper

class OmegaScansScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://omegascans.org"
        self.api_url = "https://api.omegascans.org"

    def _fetch_json(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise Exception(f"Falha ao acessar a API: {url} - {e}")

    def get_chapters(self, series_url):
        # Ex: https://omegascans.org/series/manitto
        if "/chapter-" in series_url or "/c" in series_url.split("/")[-1]:
            # It's already a chapter url
            return [series_url]

        parts = [p for p in series_url.split('/') if p]
        if not parts:
            return []
            
        series_slug = parts[-1]
        
        # 1. Obter o series_id a partir do slug
        series_info_url = f"{self.api_url}/series/{series_slug}"
        series_data = self._fetch_json(series_info_url)
        series_id = series_data.get('id')
        if not series_id:
            raise Exception(f"Não foi possível encontrar o ID da série para {series_slug}")

        # 2. Iterar sobre as páginas para pegar todos os capítulos
        chapters = []
        page = 1
        per_page = 100
        
        while True:
            query_url = f"{self.api_url}/chapter/query?page={page}&perPage={per_page}&series_id={series_id}"
            page_data = self._fetch_json(query_url)
            
            data_list = page_data.get('data', [])
            for chap in data_list:
                chap_slug = chap.get('chapter_slug')
                if chap_slug:
                    url = f"{self.base_url}/series/{series_slug}/{chap_slug}"
                    chapters.append(url)
                    
            meta = page_data.get('meta', {})
            current_page = meta.get('current_page', 1)
            last_page = meta.get('last_page', 1)
            
            if current_page >= last_page:
                break
                
            page += 1

        # A API geralmente retorna ordenado do mais novo para o mais antigo,
        # vamos usar regex para pegar o número e ordenar corretamente
        def extract_num(url):
            try:
                # Exemplo de slug: chapter-100 ou c100
                chap_part = url.split('/')[-1]
                match = re.search(r'(?:chapter|c)-?(\d+(?:\.\d+)?)', chap_part, re.IGNORECASE)
                return float(match.group(1)) if match else 0
            except Exception:
                return 0
                
        sorted_chapters = sorted(chapters, key=extract_num)
        return sorted_chapters

    def get_chapter_images(self, chapter_url):
        # Ex: https://omegascans.org/series/manitto/chapter-100
        parts = [p for p in chapter_url.split('/') if p]
        if len(parts) < 2:
            return []
            
        series_slug = parts[-2]
        chapter_slug = parts[-1]
        
        api_chapter_url = f"{self.api_url}/chapter/{series_slug}/{chapter_slug}"
        
        try:
            data = self._fetch_json(api_chapter_url)
            
            chapter_info = data.get('chapter', {})
            
            # Verificar paywall
            paywall = data.get('paywall', False)
            if paywall:
                print(f"[OmegaScans] Aviso: O capítulo {chapter_slug} está bloqueado por paywall.")
            
            chapter_data = chapter_info.get('chapter_data', {})
            images = chapter_data.get('images', [])
            
            return images
        except Exception as e:
            print(f"[OmegaScans] Erro ao obter imagens para {chapter_url}: {e}")
            return []
