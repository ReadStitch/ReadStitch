import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import List
import logging
from ..base_scraper import BaseScraper
from core.cloudflare_bypass import get_cookie_header
from core.utils.uc_manager import get_cf_session
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

class ToonGodScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "ToonGod"
        self.base_url = "https://www.toongod.org"
        self._session = None

    def _get_session(self, url):
        if not self._session:
            logger.info(f"[{self.name}] Inicializando undetected_chromedriver para bypass...")
            # If it's an AJAX POST endpoint, better to initialize session on the series page or base url
            target_url = url if "ajax" not in url else self.base_url
            self._session = get_cf_session(target_url)
            
            # Sincroniza os cookies e User-Agent para o self.headers para que o base_scraper.download_chapter consiga baixar as imagens
            cookie_dict = self._session.cookies.get_dict()
            if cookie_dict:
                self.headers['Cookie'] = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            if 'User-Agent' in self._session.headers:
                self.headers['User-Agent'] = self._session.headers['User-Agent']
            self.headers['Referer'] = target_url
            
        return self._session

    def _fetch_html(self, url, method='GET'):
        session = self._get_session(url)
        if method == 'POST':
            resp = session.post(url, headers={'Referer': self.base_url}, timeout=30)
        else:
            resp = session.get(url, timeout=30)
            
        return resp.text


    def get_chapters(self, series_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        if not series_url.endswith('/'):
            series_url += '/'
            
        if "/chapter-" in series_url or "-chapter-" in series_url:
            return [series_url]
        
        # Madara utilizes ajax/chapters/ via POST or chapters are already in GET response
        ajax_url = series_url + 'ajax/chapters/'
        
        html = ""
        try:
            # First try GET
            html = self._fetch_html(series_url, method='GET')
        except Exception as e:
            if "Cloudflare" in str(e):
                raise e
            logger.info(f"[{self.name}] GET failed, trying POST...")
            html = self._fetch_html(ajax_url, method='POST')
            
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        seen = set()
        
        # Find all wp-manga-chapter list items
        items = soup.select('li.wp-manga-chapter a')
        
        if not items:
            # Fallback to AJAX if GET returned nothing
            logger.info(f"[{self.name}] No chapters found in GET, trying AJAX POST...")
            html = self._fetch_html(ajax_url, method='POST')
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('li.wp-manga-chapter a')
            
        for item in items:
            href = item.get('href')
            if href and href != '#' and href not in seen:
                chapters.append(href)
                seen.add(href)
                
        # Some Madara themes have them sorted newest to oldest, reverse to oldest first
        def extract_chap_num(url):
            import re
            match = re.search(r'chapter-(\d+(?:[.-]\d+)?)', url, re.IGNORECASE)
            if match:
                return float(match.group(1).replace('-', '.'))
            return 0
            
        if chapters:
            chapters = sorted(chapters, key=extract_chap_num)
                
        logger.info(f"[{self.name}] Found {len(chapters)} chapters")
        return chapters

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching images for chapter: {chapter_url}")
        
        html = self._fetch_html(chapter_url, method='GET')
            
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        # Images are usually in .reading-content img
        img_tags = soup.select('.reading-content img')
        for img in img_tags:
            src = img.get('data-src') or img.get('src')
            if src:
                src = src.strip()
                if src.startswith('//'):
                    src = 'https:' + src
                images.append(src)
                
        logger.info(f"[{self.name}] Found {len(images)} images in chapter.")
        return images
