"""
manhastro_scraper.py

Scraper for manhastro.net using Playwright to bypass Cloudflare protection.
The scraper intercepts API calls made by the site's own JavaScript to discover
the real chapter and image data endpoints.
"""

import json
import re
from typing import List

from core.scrapers.base_scraper import BaseScraper


class ManhastroScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://manhastro.net"
        self.api_url = "https://api2.manhastro.net"
        self.headers.update({
            'Accept': 'application/json',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/",
        })

    def _extract_slug(self, url: str) -> str:
        """Extract manga slug from a manhastro.net URL."""
        # e.g. https://manhastro.net/manga/o-filho-imprestavel
        match = re.search(r"/manga/([^/?#]+)", url)
        if match:
            return match.group(1)
        return ""

    def _get_playwright_data(self, url: str) -> dict:
        """
        Uses Playwright to load the given page and intercept all API responses.
        Returns a dict with intercepted data keyed by URL.
        """
        from playwright.sync_api import sync_playwright
        from core.cloudflare_bypass import load_saved_cookies

        captured = {}

        def handle_response(response):
            if "api2.manhastro.net" in response.url:
                try:
                    body = response.body()
                    if body:
                        data = json.loads(body)
                        captured[response.url] = data
                        print(f"[ManhastroScraper] Captured: {response.url} -> {type(data).__name__}")
                except Exception:
                    pass

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )

            # Load saved cloudflare cookies if available
            saved = load_saved_cookies("manhastro.net")
            if saved:
                context.add_cookies(saved)
                print(f"[ManhastroScraper] Loaded {len(saved)} saved cookies")

            page = context.new_page()
            page.on("response", handle_response)

            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print(f"[ManhastroScraper] Page load warning: {e}")

            import time
            time.sleep(3)  # Wait for background requests

            browser.close()

        return captured

    def get_chapters(self, series_url: str) -> List[str]:
        slug = self._extract_slug(series_url)
        if not slug:
            print(f"[ManhastroScraper] Could not extract slug from {series_url}")
            return []

        print(f"[ManhastroScraper] Loading manga page for: {slug}")
        captured = self._get_playwright_data(series_url)

        # Find the manga detail and chapters in captured API calls
        chapters_data = None
        for api_url, data in captured.items():
            print(f"[ManhastroScraper] Checking captured: {api_url}")
            # Look for chapters list - typically a list of chapter objects or manga detail with chapters
            if isinstance(data, dict):
                if "chapters" in data or "capitulos" in data:
                    chapters_data = data.get("chapters") or data.get("capitulos")
                    break
                # Might be the manga detail directly with a chapters key
                for key in data:
                    if isinstance(data[key], list) and len(data[key]) > 0:
                        first = data[key][0]
                        if isinstance(first, dict) and ("capitulo_id" in first or "chapter_id" in first or "numero" in first):
                            chapters_data = data[key]
                            break
            elif isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict) and ("capitulo_id" in first or "chapter_id" in first):
                    chapters_data = data
                    break

        if not chapters_data:
            print(f"[ManhastroScraper] Could not find chapters in API data. Captured: {list(captured.keys())}")
            return []

        chapter_urls = []
        for chap in chapters_data:
            chap_id = chap.get("capitulo_id") or chap.get("chapter_id") or chap.get("id")
            chap_num = chap.get("numero") or chap.get("chapter") or chap.get("number") or chap_id
            if chap_id:
                chapter_urls.append(f"{self.base_url}/manga/{slug}/chapter/{chap_id}?numero={chap_num}")

        print(f"[ManhastroScraper] Found {len(chapter_urls)} chapters")
        return chapter_urls

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        print(f"[ManhastroScraper] Loading chapter: {chapter_url}")
        captured = self._get_playwright_data(chapter_url)

        images = []
        for api_url, data in captured.items():
            print(f"[ManhastroScraper] Checking image data from: {api_url}")
            if isinstance(data, dict):
                # Look for image arrays
                for key in ["images", "imagens", "pages", "paginas", "imgs"]:
                    if key in data and isinstance(data[key], list):
                        images = data[key]
                        break
                if images:
                    break
                # Check if data itself has URL-like values
                if "url" in data:
                    images = [data["url"]]
                    break
            elif isinstance(data, list):
                # Could be a direct list of image URLs
                if data and isinstance(data[0], str) and ("http" in data[0] or data[0].endswith(('.jpg', '.png', '.webp'))):
                    images = data
                    break

        # Filter to only valid URLs
        if images:
            images = [img for img in images if isinstance(img, str)]

        print(f"[ManhastroScraper] Found {len(images)} images")
        return images
