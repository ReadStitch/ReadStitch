import json
import time
from ..base_scraper import BaseScraper

class QiScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    @property
    def name(self) -> str:
        return "Qimanhwa"
        
    def _fetch_all_chapters_api_with_playwright(self, series_slug: str) -> list:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        
        def run_browser(headless):
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                try:
                    page.goto(f"https://qimanga.com/series/{series_slug}", wait_until="domcontentloaded", timeout=15000)
                except:
                    pass
                
                cf_blocked = False
                for i in range(10):
                    title = page.title()
                    if not title or ("Just a moment" in title or "Cloudflare" in title or "Attention Required" in title or "403" in title):
                        cf_blocked = True
                        page.mouse.move(150 + i*10, 150 + i*10)
                        time.sleep(2)
                    else:
                        cf_blocked = False
                        break
                        
                if headless and cf_blocked:
                    browser.close()
                    return None
                    
                js_code = f'''
                async () => {{
                    let allChapters = [];
                    let pageNum = 1;
                    let hasNext = true;
                    while(hasNext) {{
                        try {{
                            let res = await fetch(`https://api.qimanga.com/api/v1/series/{series_slug}/chapters?page=${{pageNum}}`);
                            let json = await res.json();
                            if (json.data && json.data.length > 0) {{
                                allChapters.push(...json.data);
                            }}
                            if (json.next) {{
                                pageNum++;
                            }} else {{
                                hasNext = false;
                            }}
                        }} catch (e) {{
                            break;
                        }}
                    }}
                    return allChapters;
                }}
                '''
                
                chapters = page.evaluate(js_code)
                
                if not chapters and not cf_blocked:
                    # Cloudflare silently blocked the API request
                    cf_blocked = True
                    
                if headless and cf_blocked:
                    browser.close()
                    return None
                    
                browser.close()
                return chapters

        chapters = run_browser(headless=True)
        if chapters is None or len(chapters) == 0:
            chapters = run_browser(headless=False)
            
        return chapters or []
            
    def _fetch_json_with_playwright(self, url: str) -> dict:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        
        def run_browser(headless):
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                except:
                    pass
                
                cf_blocked = False
                for i in range(10):
                    content = page.content()
                    if "Just a moment" in content or "Cloudflare" in content or "403 Forbidden" in content:
                        cf_blocked = True
                        page.mouse.move(150 + i*10, 150 + i*10)
                        time.sleep(2)
                    else:
                        cf_blocked = False
                        break
                        
                text = ""
                if not cf_blocked:
                    try:
                        text = page.locator("body").inner_text(timeout=5000)
                        import json
                        json.loads(text)
                    except Exception:
                        cf_blocked = True
                        
                if headless and cf_blocked:
                    browser.close()
                    return None
                    
                browser.close()
                return text

        text = run_browser(headless=True)
        if text is None:
            text = run_browser(headless=False)
            
        try:
            return json.loads(text)
        except Exception as e:
            raise Exception(f"Failed to parse JSON API: {e} - Content: {text[:100]}")
            
    def get_chapters(self, series_url: str) -> list[str]:
        if "/chapter" in series_url:
            return [series_url]
            
        slug = [p for p in series_url.split('/') if p][-1]
        if '?' in slug:
            slug = slug.split('?')[0]
            
        api_chapters = self._fetch_all_chapters_api_with_playwright(slug)
        
        chapters = set()
        for chap in api_chapters:
            chap_slug = chap.get('slug')
            if chap_slug:
                full_url = f"https://qimanga.com/series/{slug}/{chap_slug}"
                chapters.add(full_url)
                
        def get_chap_num(url):
            try:
                raw_num = url.split('chapter-')[-1].split('/')[0]
                if '-' in raw_num:
                    parts = raw_num.split('-')
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
        
        api_url = f"https://api.qimanga.com/api/v1/series/{series_slug}/chapters/{chapter_slug}"
        
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
