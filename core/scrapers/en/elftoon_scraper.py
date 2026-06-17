import urllib.request
import re
from ..base_scraper import BaseScraper

class ElftoonScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://elftoon.com"

    @property
    def name(self) -> str:
        return "Elftoon"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')

    def get_chapters(self, series_url):
        if "-chapter-" in series_url:
            return [series_url]
            
        try:
            html = self._fetch_html(series_url)
        except Exception as e:
            raise Exception(f"Failed to fetch series page: {e}")

        # Regex to find chapter links
        # Assuming Elftoon chapters have format: https://elftoon.com/comic-name-chapter-XXX/
        # Or they use the standard Madara/MangaStream format
        links = set()
        
        # Method 1: standard href parsing
        pattern = r'href=[\'\"](https://elftoon\.com/[^\'\"]+chapter[^\'\"]+)[\'\"]'
        found = re.findall(pattern, html)
        for link in found:
            if 'wp-content' not in link and 'plugins' not in link:
                links.add(link)

        # Ensure we have unique chapters
        def extract_num(path):
            match = re.search(r'chapter(?:-|\/)(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return sorted_links

    def get_chapter_images(self, chapter_url):
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        import time

        images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                ignore_default_args=['--enable-automation']
            )
            context = browser.new_context()
            page = context.new_page()
            Stealth().apply_stealth_sync(page)

            try:
                page.goto(chapter_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(3) # Aguarda os scripts iniciarem o AJAX
                
                # Desce a página para forçar o carregamento de imagens por lazyload
                for _ in range(10):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    time.sleep(0.5)
                    
                images_raw = page.evaluate('''() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.map(img => img.src || img.getAttribute('data-src')).filter(src => {
                        if (!src) return false;
                        const low = src.toLowerCase();
                        return (low.includes('.jpg') || low.includes('.png') || low.includes('.jpeg') || low.includes('.webp')) && !low.includes('logo') && !low.includes('avatar') && !low.includes('icon');
                    });
                }''')
                
                if images_raw:
                    images = images_raw
            except Exception as e:
                print(f"Erro ao carregar Playwright no Elftoon: {e}")
            finally:
                browser.close()

        # Deduplicate preserving order
        seen = set()
        ordered = []
        for img in images:
            if img not in seen:
                seen.add(img)
                ordered.append(img)
                
        return ordered
