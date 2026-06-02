import logging
import urllib.request
import urllib.parse as urlparse
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class NaverScraper(BaseScraper):
    """Scraper para o site Naver Webtoon."""

    @property
    def name(self):
        return "NaverWebtoon"

    def __init__(self):
        super().__init__()
        self.base_url = "https://comic.naver.com"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/",
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        })

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        parsed = urlparse.urlparse(series_url)
        qs = urlparse.parse_qs(parsed.query)
        if 'titleId' not in qs:
            raise Exception("URL inválida do Naver: 'titleId' não encontrado.")
            
        title_id = qs['titleId'][0]
        
        all_chapters = []
        page = 1
        total_pages = 1
        
        try:
            while page <= total_pages:
                api_url = f"{self.base_url}/api/article/list?titleId={title_id}&page={page}"
                req = urllib.request.Request(api_url, headers=self.headers)
                
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8', errors='ignore'))
                    
                page_info = data.get('pageInfo', {})
                total_pages = page_info.get('totalPages', 1)
                
                article_list = data.get('articleList', [])
                for chapter in article_list:
                    no = chapter.get('no')
                    if no:
                        # Append ?chapter=no so the GUI formats the chapter string easily
                        chap_url = f"{self.base_url}/webtoon/detail?titleId={title_id}&no={no}&chapter={no}"
                        all_chapters.append(chap_url)
                        
                page += 1

            # Reverse to have Chapter 1 at the beginning
            all_chapters.reverse()
            
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception(f"Falha ao obter a lista de capítulos: {e}")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens em: {chapter_url}")
        
        try:
            req = urllib.request.Request(chapter_url, headers=self.headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # The images are inside <div class="wt_viewer">
            viewer = soup.find('div', class_='wt_viewer')
            
            # Fallback if class changes
            if not viewer:
                viewer = soup.find('div', id='sectionContWide') or soup.find('div', class_='viewer_img_box')
                
            if not viewer:
                logger.warning(f"[{self.name}] Nenhuma área de visualização encontrada.")
                return []
                
            images = []
            imgs = viewer.find_all('img')
            
            for img in imgs:
                img_url = img.get('src') or img.get('data-src') or ''
                if img_url:
                    # Ignore age ratings and placeholders
                    if 'age_all' in img_url or 'age_adult' in img_url or 'age_15' in img_url or 'age_12' in img_url:
                        continue
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                        
                    if img_url not in images:
                        images.append(img_url)
                        
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception(f"Falha ao obter imagens do capítulo: {e}")
