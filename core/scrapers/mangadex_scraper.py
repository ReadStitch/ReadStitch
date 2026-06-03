import json
import re
import urllib.request
import urllib.error
import urllib.parse
from typing import List, Optional

from core.scrapers.base_scraper import BaseScraper


class MangadexScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://mangadex.org"
        self.api_url = "https://api.mangadex.org"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _get_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _extract_uuid(self, url: str) -> Optional[str]:
        # Example: https://mangadex.org/title/87f6b9ce-e555-46aa-ac26-5b48bcac5bd0/one-punch-man
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", url)
        if match:
            return match.group(1)
        return None

    def get_chapters(self, series_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching series page: {series_url}")
        series_id = self._extract_uuid(series_url)
        if not series_id:
            print(f"[{self.__class__.__name__}] Error: Could not extract Manga UUID from {series_url}")
            return []

        print(f"[{self.__class__.__name__}] Found Manga ID: {series_id}")

        # Fallback language strategy: pt-br -> pt -> en
        target_langs = ["pt-br", "pt", "en"]
        all_chapters_data = []

        # Find the first language that has chapters
        selected_lang = None
        for lang in target_langs:
            url = f"{self.api_url}/manga/{series_id}/feed?translatedLanguage[]={lang}&limit=1"
            try:
                data = self._get_json(url)
                if data.get("total", 0) > 0:
                    selected_lang = lang
                    break
            except Exception as e:
                pass
        
        if not selected_lang:
            print(f"[{self.__class__.__name__}] Could not find chapters in any target language (pt-br, pt, en). Falling back to en.")
            selected_lang = "en"

        print(f"[{self.__class__.__name__}] Fetching chapters for language: {selected_lang}")

        offset = 0
        limit = 500
        while True:
            params = {
                "translatedLanguage[]": selected_lang,
                "order[chapter]": "asc",
                "limit": str(limit),
                "offset": str(offset)
            }
            url = f"{self.api_url}/manga/{series_id}/feed?" + urllib.parse.urlencode(params)
            
            try:
                data = self._get_json(url)
            except Exception as e:
                print(f"[{self.__class__.__name__}] API Error fetching chapters: {e}")
                break
                
            items = data.get("data", [])
            if not items:
                break
                
            all_chapters_data.extend(items)
            
            if offset + limit >= data.get("total", 0):
                break
            offset += limit

        # Deduplicate by chapter number (MangaDex may have multiple scanlator groups for the same chapter)
        seen_chapters = set()
        chapter_urls = []
        for item in all_chapters_data:
            attrs = item.get("attributes", {})
            chapter_num = attrs.get("chapter")
            
            # If chapter is None, it might be a oneshot. We'll use its UUID as the seen key to not skip it.
            seen_key = chapter_num if chapter_num is not None else item["id"]
            
            if seen_key not in seen_chapters:
                seen_chapters.add(seen_key)
                
                # Format chapter name for GUI display using query parameter for robust parsing
                if chapter_num:
                    clean_name = chapter_num
                else:
                    clean_name = "Oneshot"
                
                # Store the fake GUI url with the name appended so it looks like a real path
                chapter_urls.append(f"{self.base_url}/chapter/{item['id']}?chapter={clean_name}")
                
        print(f"[{self.__class__.__name__}] Found {len(chapter_urls)} unique chapters.")
        return chapter_urls

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching images for chapter: {chapter_url}")
        chapter_id = self._extract_uuid(chapter_url)
        if not chapter_id:
            print(f"[{self.__class__.__name__}] Error: Could not extract Chapter UUID from {chapter_url}")
            return []

        try:
            url = f"{self.api_url}/at-home/server/{chapter_id}"
            data = self._get_json(url)
            
            base_url = data.get("baseUrl")
            chapter_data = data.get("chapter", {})
            hash_id = chapter_data.get("hash")
            filenames = chapter_data.get("data", [])
            
            images = []
            for filename in filenames:
                images.append(f"{base_url}/data/{hash_id}/{filename}")
                
            print(f"[{self.__class__.__name__}] Found {len(images)} images.")
            return images
        except Exception as e:
            print(f"[{self.__class__.__name__}] Failed to fetch images: {e}")
            return []
