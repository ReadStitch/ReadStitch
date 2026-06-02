import os
import re
import io
import urllib.parse
from bs4 import BeautifulSoup
from pycasso import Canvas

from playwright.sync_api import sync_playwright

from .base_scraper import BaseScraper

def dd(input_string):
    result_bytearray = bytearray()
    for index, byte in enumerate(bytes(input_string, 'utf-8')):
        if index < 3:
            byte = byte + (1 - 2 * (byte % 2))
        elif 2 < index < 6 or index == 8:
            pass
        elif index < 10:
            byte = byte + (1 - 2 * (byte % 2))
        elif 12 < index < 15 or index == 16:
            byte = byte + (1 - 2 * (byte % 2))
        elif index == len(input_string[:-1]) or index == len(input_string[:-2]):
            byte = byte + (1 - 2 * (byte % 2))
        else:
            pass
        result_bytearray.append(byte)
    return str(result_bytearray, 'utf-8')


class PiccomaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': 'https://piccoma.com/'
        }
        self.cookies = None
        self._login_failed = False

    def _login(self, page):
        if self.cookies or self._login_failed:
            return
            
        from core.services.settings_handler import SettingsHandler
        settings = SettingsHandler()
        email = settings.load("piccoma_email")
        password = settings.load("piccoma_password")
            
        if not email or not password:
            print("Email ou senha vazios nas configuraÃ§Ãµes de Login do Piccoma!")
            self._login_failed = True
            return

        try:
            page.goto("https://piccoma.com/web/acc/email/signin", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_selector('input[name="email"]', timeout=60000)
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', password)
            page.click('input[type="submit"]')
            page.wait_for_url("**/web/", timeout=10000)
        except Exception:
            pass
            
        try:
            self.cookies = page.context.cookies()
        except:
            pass

    def get_chapters(self, series_url):
        from playwright_stealth import Stealth
        
        if not series_url.startswith('http'):
            series_url = 'https://' + series_url
            
        # Support direct chapter link
        if '/viewer/' in series_url:
            return [series_url]
            
        # Ensure we get the full episode list instead of just the product page snippet
        if '/product/' in series_url and '/episodes' not in series_url:
            series_url = series_url.rstrip('/') + '/episodes?etype=E'

        chapters = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                ignore_default_args=['--enable-automation']
            )
            context = browser.new_context(user_agent=self.headers['User-Agent'])
            if self.cookies:
                context.add_cookies(self.cookies)
                
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            # Try logging in
            self._login(page)
            self.cookies = context.cookies()
            
            page.goto(series_url, timeout=60000, wait_until='domcontentloaded')
            try:
                page.wait_for_selector('#js_episodeList', timeout=15000)
            except:
                pass
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            ul = soup.find('ul', id='js_episodeList')
            if not ul:
                browser.close()
                return []

            import re
            match_id = re.search(r'/product/(\d+)', series_url)
            product_id = match_id.group(1) if match_id else series_url.rstrip('/').split('/')[-1]
            
            for li in ul.find_all('li'):
                a_tag = li.find('a')
                if not a_tag:
                    continue
                    
                title_tag = li.find('h2')
                if not title_tag:
                    continue
                    
                episode_id = a_tag.get('data-episode_id')
                if not episode_id:
                    continue
                    
                title = title_tag.text.strip()
                
                import re
                num_match = re.search(r'(\d+(?:\.\d+)?)', title)
                if num_match:
                    chapter_num = num_match.group(1)
                    url = f"https://piccoma.com/web/viewer/{product_id}/{episode_id}?chapter={chapter_num}"
                else:
                    url = f"https://piccoma.com/web/viewer/{product_id}/{episode_id}?title={urllib.parse.quote(title)}"
                    
                chapters.append(url)
                
            browser.close()
            
        return chapters

    def get_chapter_images(self, chapter_url):
        from playwright_stealth import Stealth
        import re
        images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                ignore_default_args=['--enable-automation']
            )
            context = browser.new_context(user_agent=self.headers['User-Agent'])
            if self.cookies:
                context.add_cookies(self.cookies)
                
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            self._login(page)
            self.cookies = context.cookies()
            
            # Extract product_id and episode_id from chapter_url
            # chapter_url example: https://piccoma.com/web/viewer/208853/6298024?chapter=11
            match = re.search(r'/viewer/(\d+)/(\d+)', chapter_url)
            if match:
                product_id = match.group(1)
                episode_id = match.group(2)
                
                # Go to episodes page
                episodes_url = f"https://piccoma.com/web/product/{product_id}/episodes?etype=E"
                page.goto(episodes_url, timeout=60000, wait_until='domcontentloaded')
                try:
                    el = page.wait_for_selector(f"a[data-episode_id='{episode_id}']", timeout=15000)
                    if el:
                        # Scroll into view and force click via JS
                        el.evaluate("node => { node.scrollIntoView(); node.click(); }")
                    page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                
                # Check if the modal appeared
                try:
                    btn = page.query_selector('.btn-waitfree')
                    if btn:
                        btn.evaluate("node => node.click()")
                        page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
                    
                # Finally, go to the chapter URL just in case the click didn't redirect
                if '/viewer/' not in page.url:
                    page.goto(chapter_url, timeout=60000, wait_until='domcontentloaded')
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except:
                        pass
            else:
                # Fallback if URL doesn't match expected pattern
                page.goto(chapter_url, timeout=60000, wait_until='domcontentloaded')
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            scripts = soup.find_all('script')
            pdata_script = [s.string for s in scripts if s.string and '_pdata_' in s.string]
            
            browser.close()
            
            if not pdata_script:
                return []
                
            script_content = pdata_script[0]
            
            # Extract strictly the 'path' key to avoid capturing blurry thumbnails
            pattern = r"(?:\"path\"|path|'path')\s*:\s*['\"](//[^'\"]+)['\"]"
            images = ["https:" + image for image in re.findall(pattern, script_content)]
            
            # Fallback if no images found, filtering out common thumbnail keywords
            if not images:
                pattern_fallback = r"(?<=:')[^']+(?=')"
                images = ["https:" + img for img in re.findall(pattern_fallback, script_content) if img.startswith("//") and "thumb" not in img.lower() and "blur" not in img.lower()]
            
        return images

    def get_seed(self, checksum: str, expiry_key: str) -> str:
        for num in expiry_key:
            if int(num) != 0:
                checksum = checksum[-int(num):] + checksum[:len(checksum)-int(num)]
        return checksum
        
    def download_image(self, url, output_path):
        import urllib.request
        
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in self.cookies])
        req = urllib.request.Request(url, headers={**self.headers, "Cookie": cookie_str})
        
        with urllib.request.urlopen(req) as response:
            img_bytes = response.read()
            
        checksum = url.split('/')[-2]
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        expires = qs.get('expires', [''])[0]
        
        seed = self.get_seed(checksum, expires)
        
        if seed.isupper():
            import io
            canvas = Canvas(io.BytesIO(img_bytes), (50, 50), dd(seed))
            canvas.export(mode="scramble", path=output_path, format="jpeg")
        else:
            with open(output_path, 'wb') as f:
                f.write(img_bytes)

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)
        
        images = self.get_chapter_images(chapter_url)
        if not images:
            return 0
            
        def _download(args):
            idx, url = args
            filepath = os.path.join(target_dir, f"{idx+1:03d}.jpg")
            if not os.path.exists(filepath):
                try:
                    self.download_image(url, filepath)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Erro ao baixar {url}: {e}")
                    return None
            return filepath
            
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_download, enumerate(images)))
            
        return len(images)


