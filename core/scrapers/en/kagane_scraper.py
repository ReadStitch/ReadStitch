import os
import json
from ..base_scraper import BaseScraper
from core.utils.uc_manager import get_cf_session, get_uc_driver

class KaganeScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.domain_tld = "org"
        self.base_url = "https://kagane.org"
        self.api_url = "https://kagane.org"
        self.cache_url = "https://akari.kagane.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/"
        }

    def _update_domain(self, url: str):
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc
        if domain and 'kagane' in domain:
            tld = domain.split('.')[-1]
            self.domain_tld = tld
            self.base_url = f"https://kagane.{tld}"
            self.api_url = f"https://kagane.{tld}"
            self.cache_url = f"https://akari.kagane.{tld}"
            self.headers['Origin'] = self.base_url
            self.headers['Referer'] = f"{self.base_url}/"

    def get_chapters(self, series_url):
        self._update_domain(series_url)
        if "/book/" in series_url:
            return [series_url]

        parts = [p for p in series_url.split('/') if p]
        slug = parts[-1] if parts else ""
        
        print("Kagane: Carregando lista de capítulos via undetected_chromedriver...")
        session = get_cf_session(series_url)
        
        api_endpoint = f"{self.api_url}/api/v2/series/{slug}"
        print(f"Buscando API: {api_endpoint}")
        
        res = session.get(api_endpoint)
        if res.status_code != 200:
            raise Exception(f"Falha ao acessar API Kagane: Status {res.status_code}")
            
        try:
            data = res.json()
        except:
            raise Exception("Falha ao carregar informações da série Kagane (JSON inválido)")
            
        books = data.get('series_books', []) or data.get('seriesBooks', [])
        chapters = []
        for book in books:
            book_id = book.get('book_id') or book.get('uuid')
            chapter_no = book.get('chapter_no', '')
            url = f"{self.base_url}/series/{slug}/book/{book_id}"
            if chapter_no:
                url += f"?chapter={chapter_no}"
            chapters.append(url)

        return list(reversed(chapters))

    def get_chapter_images(self, chapter_url):
        self._update_domain(chapter_url)
        clean_url = chapter_url.split('?')[0]
        parts = [p for p in clean_url.split('/') if p]
        chapter_id = parts[-1] if parts else ""
        
        if not chapter_id:
            raise Exception("Invalid chapter URL")
            
        print("Kagane: Buscando integrity token...")
        session = get_cf_session(f"{self.base_url}/")
        
        # A API do Kagane reside primariamente no .to, independente do TLD que o usuário acessou
        api_domain = "https://kagane.to"
        
        headers = session.headers.copy()
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # 1. Obter Integrity Token
        int_res = session.post(f"{api_domain}/api/integrity", json={}, headers=headers)
        if int_res.status_code != 200:
            raise Exception(f"Falha ao obter integrity token: {int_res.status_code}")
        
        try:
            int_data = int_res.json()
            integrity_token = int_data['token']
        except Exception as e:
            raise Exception(f"Falha ao interpretar integrity token (HTML retornado?): {str(e)} - {int_res.text[:100]}")

        # 2. Obter Challenge/Manifest
        challenge_url = f"{api_domain}/api/v2/books/{chapter_id}?is_datasaver=false"
        headers['x-integrity-token'] = integrity_token
        
        print(f"Kagane: Buscando manifesto para o capítulo {chapter_id}...")
        chal_res = session.post(challenge_url, headers=headers, json={})
        if chal_res.status_code != 200:
            raise Exception(f"Falha ao obter manifesto: {chal_res.status_code}")
            
        try:
            challenge_data = chal_res.json()
        except Exception as e:
            raise Exception(f"Falha ao interpretar manifesto: {str(e)}")
            
        if 'accessToken' not in challenge_data and 'access_token' not in challenge_data:
            raise Exception(f"Falha ao obter accessToken, resposta inválida: {challenge_data}")
            
        access_token = challenge_data.get('accessToken') or challenge_data.get('access_token')
        cache_url = challenge_data.get('cacheUrl') or challenge_data.get('cache_url') or "https://akari.kagane.to"
        is_new_api = 'manifest' in challenge_data and challenge_data['manifest'] is not None
        
        if is_new_api:
            pages = challenge_data.get('manifest', {}).get('pages', [])
        else:
            pages = challenge_data.get('pages', [])
            
        images = []
        for page in pages:
            # Pega o UUID novo ou velho
            page_uuid = page.get('page_id') or page.get('pageUuid') or page.get('uuid') or page.get('id')
            if page_uuid:
                if is_new_api:
                    ext = page.get('ext', 'jxl')
                    img_url = f"{cache_url}/api/v2/books/page/{chapter_id}/{page_uuid}.{ext}?token={access_token}&is_datasaver=false"
                else:
                    img_url = f"{cache_url}/api/v2/books/file/{chapter_id}/{page_uuid}?token={access_token}&is_datasaver=false"
                images.append(img_url)
                
        return images
