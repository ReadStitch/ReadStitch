import os
import urllib.request
import urllib.parse
import json
import re
import time
from .base_scraper import BaseScraper

class QiScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    @property
    def name(self) -> str:
        return "Qimanhwa"
        
    def _fetch_rendered_with_playwright(self, url: str, wait_for_selector: str = None) -> str:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            page.goto(url, wait_until="domcontentloaded")
            
            # Anti-Cloudflare simple bypass
            for i in range(10):
                title = page.title()
                if not title or ("Just a moment" in title or "Cloudflare" in title or "Attention Required" in title):
                    page.mouse.move(150 + i*10, 150 + i*10)
                    time.sleep(2)
                else:
                    break
                    
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=15000)
                except Exception:
                    pass
                    
            html = page.content()
            browser.close()
            return html
            
    def _fetch_json_with_playwright(self, url: str) -> dict:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            page.goto(url, wait_until="domcontentloaded")
            
            # Anti-Cloudflare simple bypass
            for i in range(10):
                content = page.content()
                if "Just a moment" in content or "Cloudflare" in content:
                    page.mouse.move(150 + i*10, 150 + i*10)
                    time.sleep(2)
                else:
                    break
                    
            text = page.locator("body").inner_text()
            browser.close()
            
            try:
                return json.loads(text)
            except Exception as e:
                raise Exception(f"Failed to parse JSON API: {e}")
            
    def get_chapters(self, series_url: str) -> list[str]:
        if "/chapter" in series_url:
            return [series_url]
            
        html = self._fetch_rendered_with_playwright(series_url)
        
        slug = [p for p in series_url.split('/') if p][-1]
        pattern = r'href=[\'\"](/series/' + re.escape(slug) + r'/chapter-[0-9\.-]+)[\'\"]'
        links = re.findall(pattern, html)
        
        chapters = set()
        for href in links:
            full_url = f"https://qimanhwa.com{href}" if href.startswith('/') else href
            chapters.add(full_url)
                
        def get_chap_num(url):
            try:
                # chapter-1-5 or chapter-1.5 -> float
                raw_num = url.split('chapter-')[-1].split('/')[0]
                if '-' in raw_num:
                    parts = raw_num.split('-')
                    # if e.g. 1-5 it means 1.5, otherwise just take the first part
                    if len(parts) >= 2 and parts[1].isdigit():
                        return float(f"{parts[0]}.{parts[1]}")
                    return float(parts[0])
                return float(raw_num.replace('_', '.'))
            except:
                return 0.0
                
        return sorted(list(chapters), key=get_chap_num, reverse=True)

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        parts = chapter_url.strip('/').split('/series/')
        if len(parts) < 2:
            raise Exception("URL de capítulo inválida")
        
        slug_part = parts[1]
        slugs = slug_part.split('/')
        if len(slugs) < 2:
            raise Exception("Formato de slug inválido")
            
        series_slug = slugs[0]
        chapter_slug = slugs[1]
        
        api_url = f"https://api.qimanhwa.com/api/v1/series/{series_slug}/chapters/{chapter_slug}"
        
        data = self._fetch_json_with_playwright(api_url)
        
        if data.get('requiresPurchase', False) and not data.get('images'):
            raise Exception(f"O capítulo {chapter_slug} é pago e está bloqueado.")
            
        images = data.get('images', [])
        if not images:
            raise Exception("Nenhuma imagem encontrada.")
            
        ordered = []
        for img_obj in images:
            img_url = img_obj.get('url')
            if img_url:
                ordered.append(img_url)
                
        return ordered
