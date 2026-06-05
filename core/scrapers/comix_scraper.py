import urllib.parse
import urllib.request
import re
import json
import time
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class ComixScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    @property
    def name(self) -> str:
        return "Comix.to"
        
    def _fetch_rendered_with_playwright(self, url: str) -> dict:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        import re
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge", 
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                ignore_default_args=['--enable-automation']
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0"
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            # Intercept API requests
            api_chapters = []
            
            def handle_response(response):
                if '/chapters' in response.url and 'api/v1' in response.url:
                    try:
                        data = response.json()
                        items = data.get('result', {}).get('items', [])
                        if isinstance(items, list):
                            for item in items:
                                url_path = item.get('url', '')
                                num = item.get('number', 0)
                                title = item.get('title', '')
                                
                                group = item.get('group', {})
                                group_name = group.get('name', 'Padrão') if isinstance(group, dict) else 'Padrão'
                                
                                if url_path:
                                    full_link = f"https://comix.to/{url_path.lstrip('/')}"
                                    api_chapters.append({
                                        'num': float(num) if num else 0.0,
                                        'url': full_link,
                                        'group': group_name
                                    })
                    except Exception:
                        pass
            page.on('response', handle_response)
            
            def handle_route(route):
                req_url = route.request.url
                if '/chapters' in req_url and 'limit=' in req_url:
                    req_url = re.sub(r'limit=\d+', 'limit=100', req_url)
                    route.continue_(url=req_url)
                else:
                    route.continue_()
            page.route("**/*", handle_route)
            
            page.goto(url, wait_until="domcontentloaded")
            
            # Anti-Cloudflare simple bypass
            for i in range(10):
                title = page.title()
                if not ("Just a moment" in title or "Cloudflare" in title or "Attention Required" in title):
                    break
                page.mouse.move(150 + i*10, 150 + i*10)
                time.sleep(2)
            
            # Fallback to HTML if API failed
            api_chapters = []
            page_count = 1
            
            while True:
                print(f"Lendo página {page_count} dos capítulos...")
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                items = soup.find_all(class_=re.compile('mchap-item|mchap-row'))
                
                for item in items:
                    link_tag = item.find('a', class_=re.compile('primary|chapter'))
                    if not link_tag:
                        links = item.find_all('a', href=re.compile('chapter-'))
                        if links: link_tag = links[0]
                        
                    if link_tag and link_tag.get('href') and 'chapter-' in link_tag.get('href'):
                        href = link_tag['href']
                        full_link = f"https://comix.to{href}" if href.startswith('/') else href
                        group_tag = item.find('a', class_=re.compile('group'))
                        group_name = group_tag.get_text(strip=True) if group_tag else "Padrão"
                        
                        # Use a very basic number extraction for sorting
                        num = 0.0
                        num_match = re.search(r'chapter-(\d+(?:\.\d+)?)', href)
                        if num_match:
                            num = float(num_match.group(1))
                            
                        api_chapters.append({
                            'num': num,
                            'url': full_link,
                            'group': group_name
                        })
                        
                # Procurar botão de próxima página
                try:
                    next_btn = page.query_selector('button[aria-label*="Next"]')
                    if not next_btn or next_btn.is_disabled():
                        break
                    
                    next_btn.click(force=True)
                    time.sleep(1.5) # Esperar o React renderizar a nova página
                    page_count += 1
                except Exception as e:
                    break
                    
            browser.close()
            
            # Remove duplicates by URL but keep highest number/cleanest data
            # Sort by chapter number ascending
            api_chapters.sort(key=lambda x: x['num'])
            
            groups_dict = {}
            seen_urls = set()
            for chap in api_chapters:
                u = chap['url']
                if u in seen_urls: continue
                seen_urls.add(u)
                
                g = chap['group']
                if g not in groups_dict:
                    groups_dict[g] = []
                groups_dict[g].append(u)
                
            return groups_dict

    def get_chapter_groups(self, series_url: str) -> dict[str, list[str]]:
        groups_dict = self._fetch_rendered_with_playwright(series_url)
        
        if not groups_dict:
            raise Exception("Playwright não encontrou capítulos. O Cloudflare pode ter bloqueado ou a página não carregou.")
            
        return groups_dict

    def get_chapters(self, series_url: str) -> list[str]:
        groups = self.get_chapter_groups(series_url)
        all_chaps = []
        for chaps in groups.values():
            all_chaps.extend(chaps)
        return all_chaps

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
        import time
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge", 
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
                ignore_default_args=['--enable-automation']
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            
            # Inject script to intercept JSON.parse and capture the chapter images data
            page.add_init_script("""
                window.__interceptedImages = null;
                const originalParse = JSON.parse;
                JSON.parse = new Proxy(originalParse, {
                    apply(target, thisArg, args) {
                        const parsed = Reflect.apply(target, thisArg, args);
                        try {
                            if (parsed && parsed.result && parsed.result.pages) {
                                window.__interceptedImages = parsed.result.pages;
                            } else if (parsed && parsed.chapter && parsed.chapter.images) {
                                window.__interceptedImages = parsed.chapter.images;
                            }
                        } catch (e) {}
                        return parsed;
                    }
                });
            """)
            
            page.goto(chapter_url, wait_until="domcontentloaded")
            
            # Anti-Cloudflare simple bypass
            for i in range(10):
                title = page.title()
                if not ("Just a moment" in title or "Cloudflare" in title or "Attention Required" in title):
                    break
                page.mouse.move(150 + i*10, 150 + i*10)
                time.sleep(2)
                
            time.sleep(3)
            
            api_images = []
            
            # Try to get the intercepted images from the browser JS context
            try:
                pages_data = page.evaluate("window.__interceptedImages")
                
                if pages_data:
                    if isinstance(pages_data, dict):
                        base_url = pages_data.get('baseUrl', '').rstrip('/')
                        for item in pages_data.get('items', []):
                            u = item.get('url', '')
                            if u:
                                full_url = u if u.startswith('http') else f"{base_url}/{u.lstrip('/')}"
                                if item.get('s') == 1:
                                    full_url += "#scrambled"
                                api_images.append(full_url)
                    elif isinstance(pages_data, list):
                        for item in pages_data:
                            u = item.get('url', '')
                            if u:
                                full_url = u
                                if item.get('s') == 1:
                                    full_url += "#scrambled"
                                api_images.append(full_url)
            except Exception as e:
                print("Erro ao coletar window.__interceptedImages:", e)
                
            if api_images:
                browser.close()
                return api_images
                
            # FALLBACK: O Comix carrega as imagens via scroll (lazy load)
            print("Interceptação JSON falhou. Usando scroll manual...")
            for _ in range(150):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(0.3)
                is_bottom = page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight")
                if is_bottom:
                    # Tentar esperar para ver se mais imagens carregam no final
                    time.sleep(1)
                    is_bottom_after = page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight")
                    if is_bottom_after:
                        break
                        
            time.sleep(1)
            
            # Coletar as imagens renderizadas
            try:
                images = page.evaluate('''() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.map(img => img.src || img.getAttribute('data-src')).filter(src => {
                        if (!src) return false;
                        const low = src.toLowerCase();
                        return low.includes('.jpg') || low.includes('.png') || low.includes('.jpeg') || low.includes('.webp');
                    });
                }''')
            except Exception:
                images = []
                
            browser.close()
            
            if not images and not api_images:
                raise Exception("Playwright não encontrou as imagens. O capítulo pode usar canvas ofuscado ou não carregou.")
                
            # Filtrar duplicatas mantendo a ordem
            seen = set()
            ordered = []
            for img in images:
                if img not in seen:
                    seen.add(img)
                    ordered.append(img)
                    
            return ordered

    def download_image(self, url, output_path):
        import urllib.request
        from io import BytesIO
        from PIL import Image
        
        is_scrambled = url.endswith("#scrambled")
        clean_url = url.split("#")[0]
        
        req = urllib.request.Request(clean_url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            data = response.read()
            seed = response.headers.get("x-scramble-seed")
            
            if is_scrambled and seed and int(seed) != 0:
                self._descramble_and_save(data, int(seed), output_path)
            else:
                with open(output_path, 'wb') as f:
                    f.write(data)

    def _descramble_and_save(self, image_bytes, seed, output_path):
        from PIL import Image
        from io import BytesIO
        
        GRID_COLS = 5
        GRID_ROWS = 5
        NUM_TILES = GRID_COLS * GRID_ROWS
        
        # Linear Congruential Generator logic for building the order array
        arr = list(range(NUM_TILES))
        state = seed & 0xFFFFFFFF
        for i in range(NUM_TILES - 1, 0, -1):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            j = state % (i + 1)
            arr[i], arr[j] = arr[j], arr[i]
            
        perm = arr
        
        # Load the scrambled image
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGBA")  # Ensure we have a workable color mode
            width, height = img.size
            tile_w = width // GRID_COLS
            tile_h = height // GRID_ROWS
            
            output = Image.new("RGBA", (width, height))
            
            for src_idx in range(NUM_TILES):
                dst_idx = perm[src_idx]
                
                src_col = src_idx % GRID_COLS
                src_row = src_idx // GRID_COLS
                dst_col = dst_idx % GRID_COLS
                dst_row = dst_idx // GRID_COLS
                
                src_rect = (
                    src_col * tile_w,
                    src_row * tile_h,
                    (src_col + 1) * tile_w,
                    (src_row + 1) * tile_h,
                )
                
                # Crop tile from source
                tile = img.crop(src_rect)
                
                dst_x = dst_col * tile_w
                dst_y = dst_row * tile_h
                
                # Paste tile to output
                output.paste(tile, (dst_x, dst_y))
                
            # Convert back to RGB for JPEG saving
            if output.mode == "RGBA":
                bg = Image.new("RGB", output.size, (255, 255, 255))
                bg.paste(output, mask=output.split()[3]) # 3 is the alpha channel
                output = bg
                
            output.save(output_path, format="JPEG", quality=90)
