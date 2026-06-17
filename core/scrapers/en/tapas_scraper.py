import json
import re
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
from core.scrapers.base_scraper import BaseScraper

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://m.tapas.io",
}


class TapasScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://tapas.io"
        # Use a cookie-aware opener so session cookies persist across requests
        self._cj = CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cj)
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _get(self, url: str) -> str:
        """Perform a GET and return the decoded body."""
        req = urllib.request.Request(url, headers=_HEADERS)
        with self._opener.open(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        """GET and parse JSON."""
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        body = self._get(url)
        return json.loads(body)

    @staticmethod
    def _extract_series_id(html: str) -> Optional[str]:
        match = re.search(r'\"seriesId\"\s*:\s*(\d+)', html)
        if match:
            return match.group(1)

        soup = BeautifulSoup(html, "html.parser")
        btn = soup.find("a", class_=re.compile(r"subscribe-btn"))
        if btn and btn.has_attr("data-id"):
            return btn["data-id"]

        for el in soup.find_all(attrs={"data-series-id": True}):
            return el["data-series-id"]

        match2 = re.search(r"series_id\s*=\s*[\"']?(\d+)", html)
        if match2:
            return match2.group(1)

        return None

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def get_chapters(self, series_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching series page: {series_url}")

        try:
            html = self._get(series_url)
            series_id = self._extract_series_id(html)
            if not series_id:
                print(f"[{self.__class__.__name__}] Error: Could not extract numeric series ID from {series_url}")
                return []

            print(f"[{self.__class__.__name__}] Found Series ID: {series_id}")

            chapters: list[str] = []
            page = 1

            while True:
                episodes_url = f"{self.base_url}/series/{series_id}/episodes"
                params = {"page": str(page), "sort": "NEWEST", "large": "true"}

                print(f"[{self.__class__.__name__}] Fetching episodes page {page}...")
                data = self._get_json(episodes_url, params)

                if "data" not in data or "episodes" not in data["data"]:
                    break

                episodes = data["data"]["episodes"]
                if not episodes:
                    break

                for ep in episodes:
                    is_free = ep.get("free", False)
                    is_unlocked = ep.get("unlocked", False)

                    if is_free or is_unlocked:
                        ep_id = ep.get("id")
                        title = ep.get("title", f"Episode {ep_id}")

                        clean_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
                        clean_title = clean_title.replace(" ", "_")
                        if not clean_title:
                            clean_title = f"Episode_{ep_id}"

                        # Use /comic/ instead of /episode/ to bypass GUI regex
                        chapter_url = f"{self.base_url}/comic/{ep_id}/{clean_title}"
                        chapters.append(chapter_url)

                pagination = data["data"].get("pagination", {})
                if not pagination.get("has_next", False):
                    break

                page += 1

            print(f"[{self.__class__.__name__}] Found {len(chapters)} free chapters.")
            return chapters

        except Exception as e:
            print(f"[{self.__class__.__name__}] Failed to fetch chapters: {e}")
            return []

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching images for chapter: {chapter_url}")

        try:
            # Reconstruct the real URL
            # e.g. https://tapas.io/comic/12345/Episode_1 -> https://tapas.io/episode/12345
            parts = chapter_url.split("/")
            if len(parts) >= 5 and parts[3] == "comic":
                real_url = f"{self.base_url}/episode/{parts[4]}"
            else:
                real_url = chapter_url

            html = self._get(real_url)
            soup = BeautifulSoup(html, "html.parser")
            images: list[str] = []

            for img in soup.select("img.content__img"):
                src = img.get("data-src") or img.get("src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = self.base_url + src
                    images.append(src)

            print(f"[{self.__class__.__name__}] Found {len(images)} images.")
            return images

        except Exception as e:
            print(f"[{self.__class__.__name__}] Failed to fetch images: {e}")
            return []
