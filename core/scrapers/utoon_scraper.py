import os
import re
import time
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class UtoonScraper(BaseScraper):
    def __init__(self):
        super().__init__()

    def _launch_chrome_cdp(self, profile_dir, headless=False):
        import subprocess
        import time
        import os
        
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            
        cmd = [
            chrome_path,
            "--remote-debugging-port=9223",
            "--user-data-dir=" + profile_dir,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars"
        ]
        if headless:
            cmd.append("--headless=new")
            
        process = subprocess.Popen(cmd)
        time.sleep(3) # Aguarda porta abrir
        return process

    def _get_page_content_with_playwright(self, url: str, wait_selector: str = None) -> str:
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_utoon_browser")
        os.makedirs(profile_dir, exist_ok=True)
        
        def run_browser(headless):
            chrome_process = self._launch_chrome_cdp(profile_dir, headless=headless)
            
            def _do_fetch():
                from playwright.sync_api import sync_playwright
                import time
                
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp("http://localhost:9223")
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else context.new_page()
                    
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    except Exception as e:
                        print("Goto timeout:", e)
                    
                    cf_blocked = False
                    for _ in range(10 if headless else 180):
                        try:
                            title = page.title().strip()
                            if title and "Just a moment" not in title and "Cloudflare" not in title:
                                break
                        except:
                            pass
                        time.sleep(1)
                    else:
                        if headless:
                            cf_blocked = True
                    
                    if headless and cf_blocked:
                        try:
                            browser.close()
                        except: pass
                        time.sleep(2) 
                        return None
                        
                    if "manga/" in url and "chapter-" not in url:
                        for retry in range(5):
                            try:
                                page.wait_for_load_state("domcontentloaded", timeout=5000)
                                chapters_html = page.evaluate('''() => {
                                    let base = window.location.href.split('?')[0].replace(/\\/$/, '');
                                    return fetch(base + '/ajax/chapters/', {
                                        method: 'POST'
                                    }).then(res => res.text());
                                }''')
                                
                                if chapters_html and len(chapters_html) > 100 and "chapter" in chapters_html.lower():
                                    try: browser.close()
                                    except: pass
                                    return chapters_html
                            except Exception as e:
                                time.sleep(2)
                                continue
                        print("AJAX fallback via evaluate falhou após 5 tentativas.")
                            
                    if "chapter-" in url:
                        for _ in range(30):
                            try: page.evaluate("window.scrollBy(0, 1500)")
                            except: pass
                            time.sleep(0.5)
                            
                    try: html = page.content()
                    except: html = ""
                    
                    try: browser.close()
                    except: pass
                    return html

            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_do_fetch)
                    return future.result()
            finally:
                import subprocess
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(chrome_process.pid)], capture_output=True)
                except:
                    pass
                chrome_process.terminate()

        # Primeira tentativa invisível
        html = run_browser(headless=True)
        if html is None:
            print("Utoon: Cloudflare detectado! Abrindo janela visível para você resolver o captcha...")
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
