import urllib.request
import urllib.parse
import re
from ..base_scraper import BaseScraper

class DuskScansScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://duskscans.com"

    def get_chapters(self, series_url):
        """
        Fetches the series page and extracts a list of all chapter URLs.
        Returns a sorted list of absolute chapter URLs.
        """
        if "/chapter-" in series_url:
            return [series_url]

        req = urllib.request.Request(series_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                final_url = response.geturl()
                html = response.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to fetch series page: {e}")

        # Extrair o slug
        path = urllib.parse.urlparse(final_url).path.strip('/')
        parts = [p for p in path.split('/') if p]
        
        if not parts:
            return []
            
        slug = parts[-1]
        
        # Encontrar os links dos capítulos
        pattern = r'href=[\'\"](/series/' + re.escape(slug) + r'/chapter-[^\'\"]+)[\'\"]'
        links = set(re.findall(pattern, html))
        
        def extract_num(path):
            match = re.search(r'chapter-(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return [self.base_url + l for l in sorted_links]

    def get_chapter_images(self, chapter_url):
        """
        Fetches the chapter page and extracts all image URLs.
        """
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            print(f"[DuskScansScraper] Falha ao buscar capítulo: {e}")
            return []

        # Imagens ficam no cdn em /storage/uploads/chapters/
        pattern = r'src=[\'\"](https://cdn\.duskscans\.com/storage/uploads/chapters/[^\'\"]+)[\'\"]'
        images = re.findall(pattern, html)
        
        return list(dict.fromkeys(images))  # Remove duplicates keeping order

