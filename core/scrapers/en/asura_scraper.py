import urllib.request
import re
from ..base_scraper import BaseScraper

class AsuraScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://asurascans.com"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')

    def get_chapters(self, series_url):
        """
        Fetches the series page and extracts a list of all chapter URLs.
        Returns a sorted list of absolute chapter URLs.
        If a chapter URL is provided, returns just that chapter.
        """
        if "/chapter/" in series_url:
            return [series_url]
            
        try:
            html = self._fetch_html(series_url)
        except Exception as e:
            raise Exception(f"Failed to fetch series page: {e}")

        # Extract slug from URL
        slug = [p for p in series_url.split('/') if p][-1]
        
        # Regex to find /comics/slug/chapter/X
        pattern = r'href=[\'\"](/comics/' + re.escape(slug) + r'/chapter/[^\'\"]+)[\'\"]'
        links = set(re.findall(pattern, html))
        
        def extract_num(path):
            match = re.search(r'chapter(?:-|\/)(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return [self.base_url + l for l in sorted_links]

    def get_chapter_images(self, chapter_url):
        """
        Fetches the chapter page and extracts all image URLs.
        """
        try:
            html = self._fetch_html(chapter_url)
        except Exception as e:
            raise Exception(f"Failed to fetch chapter page: {e}")
            
        # Asura stores JSON props in HTML where quotes are HTML-escaped.
        html = html.replace('&quot;', '"')
        
        images = re.findall(r'https://cdn\.asurascans\.com/asura-images/chapters/[^\"\']+\.(?:webp|jpg|png)', html)
        
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for img in images:
            if img not in seen:
                seen.add(img)
                ordered.append(img)
                
        return ordered
