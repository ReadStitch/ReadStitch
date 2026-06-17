import json
import re
import urllib.request
import urllib.parse
from typing import List
from bs4 import BeautifulSoup

from core.scrapers.base_scraper import BaseScraper


class AstratoonsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://new.astratoons.com"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/",
            "Accept": "application/json, text/plain, */*",
        }

    def get_chapters(self, series_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching series page: {series_url}")
        
        req = urllib.request.Request(series_url, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8")
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error loading series page: {e}")
            return []

        # Find comicId
        # comicId: 1234
        match = re.search(r'comicId:\s*(\d+)', html)
        if not match:
            print(f"[{self.__class__.__name__}] Could not extract comicId from the page.")
            return []
            
        manga_id = match.group(1)
        print(f"[{self.__class__.__name__}] Found comicId: {manga_id}")
        
        page = 1
        has_more = True
        chapters = []
        
        while has_more:
            api_url = f"{self.base_url}/api/comics/{manga_id}/chapters?search=&order=desc&page={page}"
            api_req = urllib.request.Request(api_url, headers=self._headers)
            try:
                with urllib.request.urlopen(api_req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"[{self.__class__.__name__}] Error fetching chapters API page {page}: {e}")
                break
                
            chapters_html = data.get("html", "")
            if not chapters_html:
                break
                
            soup = BeautifulSoup(chapters_html, "html.parser")
            links = soup.find_all("a", href=True)
            for a in links:
                href = a["href"]
                if href.startswith("/"):
                    href = self.base_url + href
                elif not href.startswith("http"):
                    href = self.base_url + "/" + href
                    
                if href not in chapters:
                    chapters.append(href)
            
            has_more = data.get("hasMore", False)
            page += 1
            
        print(f"[{self.__class__.__name__}] Found {len(chapters)} chapters.")
        return chapters

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching images for chapter: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8")
        except Exception as e:
            print(f"[{self.__class__.__name__}] Error fetching chapter page: {e}")
            return []
            
        soup = BeautifulSoup(html, "html.parser")
        reader_container = soup.find(id="reader-container")
        
        if not reader_container:
            print(f"[{self.__class__.__name__}] Could not find #reader-container in the page.")
            return []
            
        images = []
        
        # O Tachiyomi busca img[src] e canvas[data-src]
        elements = reader_container.find_all(["img", "canvas"])
        for el in elements:
            src = el.get("src")
            data_src = el.get("data-src")
            
            img_url = src if src else data_src
            if img_url:
                if img_url.startswith("/"):
                    img_url = self.base_url + img_url
                if img_url not in images:
                    images.append(img_url)
                    
        print(f"[{self.__class__.__name__}] Found {len(images)} images.")
        return images
