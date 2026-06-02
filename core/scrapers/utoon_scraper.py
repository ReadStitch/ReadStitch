import os
import re
import time
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class UtoonScraper(BaseScraper):
    def __init__(self):
        super().__init__()

    def _get_page_content_with_playwright(self, url: str, wait_selector: str = None) -> str:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_browser")
        os.makedirs(profile_dir, exist_ok=True)
        
        def run_browser(headless):
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="msedge",
                    headless=headless,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print("Goto timeout:", e)
                
                # Check for Cloudflare by waiting for the target selector
                # If it doesn't appear in 8 seconds, we assume Cloudflare blocked us
                cf_blocked = False
                
                if wait_selector:
                    try:
                        # Em headless, esperamos pouco. Em headless=False, esperamos muito.
                        timeout = 10000 if headless else 180000
                        page.wait_for_selector(wait_selector, timeout=timeout)
                    except Exception:
                        if headless:
                            cf_blocked = True
                
                # Se estivermos com a janela invisível e bloqueou, abortamos para reabrir visível
                if headless and cf_blocked:
                    context.close()
                    time.sleep(2) 
                    return None
                    
                if "manga/" in url and "chapter-" not in url:
                    try:
                        chapters_html = page.evaluate('''() => {
                            let base = window.location.href.split('?')[0].replace(/\\/$/, '');
                            return fetch(base + '/ajax/chapters/', {
                                method: 'POST'
                            }).then(res => res.text());
                        }''')
                        
                        if chapters_html and len(chapters_html) > 100 and "chapter" in chapters_html.lower():
                            context.close()
                            return chapters_html
                    except Exception as e:
                        print("AJAX fallback via evaluate falhou:", e)
                        
                if "chapter-" in url:
                    for _ in range(30):
                        page.evaluate("window.scrollBy(0, 1500)")
                        time.sleep(0.5)
                        
                html = page.content()
                context.close()
                return html

        # Primeira tentativa invisível
        html = run_browser(headless=True)
        if html is None:
            print("Cloudflare detectado! Abrindo janela visível para você resolver o captcha...")
            html = run_browser(headless=False)
            
        return html

    def get_chapters(self, series_url):
        if "chapter-" in series_url or "/chapter" in series_url:
            return [series_url]
            
        try:
            html = self._get_page_content_with_playwright(series_url, wait_selector='.wp-manga-chapter')
        except Exception as e:
            raise Exception(f"Failed to fetch Utoon series: {e}")

        parts = [p for p in series_url.split('/') if p]
        slug = parts[-1] if parts else ""
        
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"utoon.net/manga/{slug}/chapter-" in href:
                links.add(href)
        
        def extract_num(path):
            match = re.search(r'chapter-(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return sorted_links

    def get_chapter_images(self, chapter_url):
        try:
            html = self._get_page_content_with_playwright(chapter_url, wait_selector='.wp-manga-chapter-img, .page-break img')
        except Exception as e:
            raise Exception(f"Failed to fetch Utoon chapter: {e}")
            
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        imgs = soup.find_all('img', class_=re.compile(r'wp-manga-chapter-img'))
        if not imgs:
            container = soup.find('div', class_='reading-content')
            if container:
                imgs = container.find_all('img')
                
        for img in imgs:
            src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
            if src:
                src = src.strip()
                if src.startswith('//'):
                    src = 'https:' + src
                images.append(src)
        
        seen = set()
        ordered = []
        for img in images:
            if img not in seen:
                seen.add(img)
                ordered.append(img)
                
        if not ordered:
            ordered = list(dict.fromkeys(re.findall(r'(https://utoon\.net/wp-content/uploads/[^\s\'\"]+)', html)))
            
        return ordered
