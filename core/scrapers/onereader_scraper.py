import urllib.request
import json
import re
from typing import List

from core.scrapers.base_scraper import BaseScraper


class OneReaderScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://onereader.net"
        self.api_url = "https://api.onereader.net/api"
        self.headers.update({
            'Accept': 'application/json',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/",
        })

    def _extract_slug(self, url: str) -> str:
        # Example: https://onereader.net/manga/regressao-promotor-mestre
        # Example: https://onereader.net/manga-details?id=antigo-corpo-sagrado
        match = re.search(r"(?:/manga/|\?id=)([^/?&]+)", url)
        if match:
            return match.group(1)
        return ""

    def get_chapters(self, series_url: str) -> List[str]:
        slug = self._extract_slug(series_url)
        if not slug:
            print(f"[{self.__class__.__name__}] Could not extract slug from {series_url}")
            return []

        url = f"{self.api_url}/chapters/{slug}"
        print(f"[{self.__class__.__name__}] Fetching chapters from {url}")

        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            chapter_urls = []
            
            # data is a dict mapping chapter numbers to chapter objects
            # Example keys: '1', '2', '3', '3.5', etc.
            if isinstance(data, dict):
                # Sort numerically, treating '3.5' as a float
                def _sort_key(k):
                    try:
                        return float(k)
                    except ValueError:
                        return 0.0
                
                sorted_keys = sorted(data.keys(), key=_sort_key)
                for key in sorted_keys:
                    chapter_urls.append(f"{self.base_url}/chapter/{slug}/{key}")
                    
            print(f"[{self.__class__.__name__}] Found {len(chapter_urls)} chapters")
            return chapter_urls
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error fetching chapters: {e}")
            return []

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        # Example chapter_url: https://onereader.net/chapter/regressao-promotor-mestre/1
        match = re.search(r"/chapter/([^/]+)/([^/?]+)", chapter_url)
        if not match:
            print(f"[{self.__class__.__name__}] Could not extract slug and chapter num from {chapter_url}")
            return []
            
        slug = match.group(1)
        chapter_num = match.group(2)
        
        api_endpoint = f"{self.api_url}/chapters/{slug}/{chapter_num}"
        print(f"[{self.__class__.__name__}] Fetching images from {api_endpoint}")

        req = urllib.request.Request(api_endpoint, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            if isinstance(data, dict) and 'pages' in data:
                images = data['pages']
                print(f"[{self.__class__.__name__}] Found {len(images)} images")
                return images
            else:
                print(f"[{self.__class__.__name__}] Unexpected response format")
                return []
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error fetching images: {e}")
            return []
