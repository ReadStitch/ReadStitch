import json
import urllib.request
from bs4 import BeautifulSoup
from urllib.error import HTTPError
from ..base_scraper import BaseScraper

class FlameComicsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://flamecomics.xyz"
        self.cdn_url = "https://cdn.flamecomics.xyz"
        self.build_id = None

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        except HTTPError as e:
            if e.code == 403:
                # Se der 403, pode ser Cloudflare limitando o Python
                # Vamos tentar com o scraper de bypass padrão se estiver disponível
                try:
                    import cloudscraper
                    scraper = cloudscraper.create_scraper()
                    return scraper.get(url, headers=self.headers).text
                except Exception:
                    pass
            raise e

    def _get_build_id(self):
        if self.build_id:
            return self.build_id
            
        html = self._fetch_html(self.base_url)
        soup = BeautifulSoup(html, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if not next_data_script:
            raise Exception("Não foi possível encontrar __NEXT_DATA__ no Flame Comics")
            
        data = json.loads(next_data_script.string)
        self.build_id = data.get('buildId')
        
        if not self.build_id:
            raise Exception("BuildId não encontrado no JSON do Flame Comics")
            
        return self.build_id

    def _fetch_api_json(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            if e.code == 404:
                # 404 geralmente significa que o buildId mudou e as URLs antigas estão obsoletas.
                # Limpamos o buildId e tentamos de novo.
                self.build_id = None
                return None
            elif e.code == 403:
                try:
                    import cloudscraper
                    scraper = cloudscraper.create_scraper()
                    res = scraper.get(url, headers=self.headers)
                    if res.status_code == 200:
                        return res.json()
                except Exception:
                    pass
            raise e

    def get_chapters(self, series_url):
        # Exemplo de URL: https://flamecomics.xyz/series/1000000002
        parts = [p for p in series_url.split('/') if p]
        series_id = parts[-1]
        
        build_id = self._get_build_id()
        api_url = f"{self.base_url}/_next/data/{build_id}/series/{series_id}.json?id={series_id}"
        
        data = self._fetch_api_json(api_url)
        if data is None:
            # Tenta novamente com novo buildId
            build_id = self._get_build_id()
            api_url = f"{self.base_url}/_next/data/{build_id}/series/{series_id}.json?id={series_id}"
            data = self._fetch_api_json(api_url)
            
        if not data or 'pageProps' not in data:
            raise Exception("Falha ao carregar capítulos do Flame Comics")
            
        chapters_data = data['pageProps'].get('chapters', [])
        
        chapters = []
        for chap in chapters_data:
            # Ex: https://flamecomics.xyz/series/1000000002/chapter-1-token
            chap_token = chap.get('token')
            chap_num = chap.get('chapter', '')
            
            if chap_num is not None and chap_num != '':
                try:
                    f_num = float(chap_num)
                    if f_num == int(f_num):
                        chap_num = int(f_num)
                    else:
                        chap_num = f_num
                except (ValueError, TypeError):
                    pass
            if chap_token:
                url = f"{self.base_url}/series/{series_id}/{chap_token}"
                if chap_num:
                    url += f"?chapter={chap_num}"
                chapters.append(url)
                
        # Retorna a lista na ordem correta (geralmente a API retorna do mais novo pro mais velho)
        return list(reversed(chapters))

    def get_chapter_images(self, chapter_url):
        clean_url = chapter_url.split('?')[0]
        parts = [p for p in clean_url.split('/') if p]
        if len(parts) < 2:
            raise Exception("URL de capítulo inválida")
            
        series_id = parts[-2]
        token = parts[-1]
        
        build_id = self._get_build_id()
        api_url = f"{self.base_url}/_next/data/{build_id}/series/{series_id}/{token}.json?id={series_id}&token={token}"
        
        data = self._fetch_api_json(api_url)
        if data is None:
            # Tenta novamente com novo buildId
            build_id = self._get_build_id()
            api_url = f"{self.base_url}/_next/data/{build_id}/series/{series_id}/{token}.json?id={series_id}&token={token}"
            data = self._fetch_api_json(api_url)
            
        if not data or 'pageProps' not in data:
            raise Exception("Falha ao carregar imagens do capítulo do Flame Comics")
            
        chapter_data = data['pageProps'].get('chapter', {})
        images_data = chapter_data.get('images', [])
        release_date = chapter_data.get('release_date', '')
        
        if isinstance(images_data, dict):
            images_list = list(images_data.values())
        else:
            images_list = images_data
            
        image_urls = []
        for img in images_list:
            img_name = img.get('name')
            if not img_name:
                continue
                
            # Tratamento para imagens compostas (split image fixer)
            # A extensão original lida com "?comp" e "%7C" para unir metades horizontais.
            # Vamos simplesmente extrair todas as URLs individuais e adicioná-las na lista.
            # O ReadStitch vai baixá-las individualmente e costurar tudo.
            if "%7C" in img_name:
                sub_names = img_name.split("%7C")
                for sub in sub_names:
                    clean_sub = sub.replace("?comp", "")
                    img_url = f"{self.cdn_url}/uploads/images/series/{series_id}/{token}/{clean_sub}?{release_date}"
                    image_urls.append(img_url)
            else:
                img_url = f"{self.cdn_url}/uploads/images/series/{series_id}/{token}/{img_name}?{release_date}"
                image_urls.append(img_url)
                
        return image_urls
