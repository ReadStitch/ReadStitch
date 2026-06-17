import urllib.request
import json
from ..base_scraper import BaseScraper

class EzmangaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://ezmanga.org"
        self.api_url = "https://vapi.ezmanga.org/api/v1/series/{series_slug}/chapters"
        self.chapter_api_url = "https://vapi.ezmanga.org/api/v1/series/{series_slug}/chapters/{chapter_slug}"

    def get_chapters(self, series_url):
        """
        Returns a list of chapter URLs for the given series URL.
        """
        # Ex: https://ezmanga.org/series/purely-delinquent
        parts = [p for p in series_url.split('/') if p]
        
        # If it's already a chapter URL, return just this chapter
        if "chapter-" in parts[-1] or "chapter" in parts[-1]:
            return [series_url]
            
        series_slug = parts[-1]
        
        api_endpoint = self.api_url.format(series_slug=series_slug)
        req = urllib.request.Request(api_endpoint, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise Exception(f"Failed to fetch chapters API: {e}")
            
        chapters_data = data.get('data', [])
        
        # We want to return absolute URLs.
        # Ensure we sort them from earliest to latest based on the 'number' field.
        chapters_data.sort(key=lambda x: x.get('number', 0))
        
        # Return URLs formatted like: https://ezmanga.org/series/purely-delinquent/chapter-X
        chapter_urls = [f"{self.base_url}/series/{series_slug}/{c['slug']}" for c in chapters_data]
        return chapter_urls

    def get_chapter_images(self, chapter_url):
        """
        Returns a list of image URLs for the given chapter URL.
        """
        # Ex: https://ezmanga.org/series/purely-delinquent/chapter-1
        parts = [p for p in chapter_url.split('/') if p]
        chapter_slug = parts[-1]
        series_slug = parts[-2]
        
        api_endpoint = self.chapter_api_url.format(series_slug=series_slug, chapter_slug=chapter_slug)
        req = urllib.request.Request(api_endpoint, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise Exception(f"Failed to fetch chapter images API: {e}")
            
        images_data = data.get('images', [])
        
        # Sort by 'order' if available
        images_data.sort(key=lambda x: x.get('order', 0))
        
        image_urls = [img['url'] for img in images_data if 'url' in img]
        return image_urls
