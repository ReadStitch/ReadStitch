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
                # Block ads and trackers to speed up load significantly
                if any(x in req_url for x in ["google-analytics", "doubleclick", "adsystem", "quantserve", "facebook", "hotjar"]):
                    route.abort()
                elif '/chapters' in req_url and 'limit=' in req_url:
                    req_url = re.sub(r'limit=\d+', 'limit=100', req_url)
                    route.continue_(url=req_url)
                else:
                    route.continue_()
            page.route("**/*", handle_route)
            
            try:
                page.goto(url, wait_until="commit", timeout=20000)
            except Exception:
                pass
            
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            
            # Anti-Cloudflare simple bypass
            for i in range(10):
                title = page.title()
                if not ("Just a moment" in title or "Cloudflare" in title or "Attention Required" in title):
                    break
                page.mouse.move(150 + i*10, 150 + i*10)
                time.sleep(2)
            
            # Fallback to HTML if API failed
            if not api_chapters:
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
                            if (parsed) {
                                if (parsed.result && parsed.result.pages) {
                                    window.__interceptedImages = parsed.result.pages;
                                } else if (parsed.chapter && parsed.chapter.images) {
                                    window.__interceptedImages = parsed.chapter.images;
                                } else if (parsed.images) {
                                    window.__interceptedImages = parsed.images;
                                } else if (parsed.pages) {
                                    window.__interceptedImages = parsed.pages;
                                }
                            }
                        } catch (e) {}
                        return parsed;
                    }
                });
            """)
            
            # Also capture via Network response events (newer fetch APIs use response.json() bypassing JSON.parse)
            def handle_chapter_response(response):
                if '/chapter/' in response.url and 'api/v1' in response.url:
                    try:
                        parsed = response.json()
                        if parsed:
                            if parsed.get('result', {}).get('pages'):
                                page.evaluate("val => { window.__interceptedImages = val; }", parsed['result']['pages'])
                            elif parsed.get('chapter', {}).get('images'):
                                page.evaluate("val => { window.__interceptedImages = val; }", parsed['chapter']['images'])
                            elif parsed.get('images'):
                                page.evaluate("val => { window.__interceptedImages = val; }", parsed['images'])
                            elif parsed.get('pages'):
                                page.evaluate("val => { window.__interceptedImages = val; }", parsed['pages'])
                    except Exception:
                        pass
            page.on('response', handle_chapter_response)
            
            try:
                page.goto(chapter_url, wait_until="commit", timeout=20000)
            except Exception:
                pass
            
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            
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
                        for index, item in enumerate(pages_data.get('items', [])):
                            u = item.get('url', '')
                            if u:
                                full_url = u if u.startswith('http') else f"{base_url}/{u.lstrip('/')}"
                                is_scrambled = item.get('s') == 1 or (index + 1) % 4 == 0
                                if is_scrambled:
                                    full_url += "#scrambled"
                                api_images.append(full_url)
                    elif isinstance(pages_data, list):
                        for index, item in enumerate(pages_data):
                            u = item.get('url', '')
                            if u:
                                full_url = u
                                is_scrambled = item.get('s') == 1 or (index + 1) % 4 == 0
                                if is_scrambled:
                                    full_url += "#scrambled"
                                api_images.append(full_url)
            except Exception as e:
                print("Erro ao coletar window.__interceptedImages:", e)
                
            if api_images:
                browser.close()
                return api_images
                
            # FALLBACK: O Comix carrega as imagens via scroll (lazy load)
            print("Interceptação JSON falhou. Usando scroll manual...")
            for _ in range(80):
                page.evaluate("window.scrollBy(0, 1500)")
                time.sleep(0.25)
                is_bottom = page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight")
                if is_bottom:
                    time.sleep(1)
                    break
                        
            time.sleep(1.5)
            
            # Coletar as imagens renderizadas
            try:
                images = page.evaluate('''() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.map(img => img.getAttribute('data-src') || img.getAttribute('data-srcset') || img.src || img.getAttribute('src')).filter(src => {
                        if (!src) return false;
                        const low = src.toLowerCase();
                        // Ignore small placeholders/avatars/icons
                        if (low.includes('avatar') || low.includes('logo') || low.includes('icon') || low.includes('profile')) return false;
                        return low.includes('.jpg') || low.includes('.png') || low.includes('.jpeg') || low.includes('.webp') || src.startsWith('data:image');
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
            
            # Check for the brand new x-enc-seed / x-enc-len headers (from Tachiyomi/Keiyoushi updates)
            enc_seed = response.headers.get("x-enc-seed")
            enc_len = response.headers.get("x-enc-len")
            scramble_seed = response.headers.get("x-scramble-seed")
            
            if enc_seed and enc_len and int(enc_seed) != 0:
                # Decrypt using the new LCG byte-stream method
                decrypted_data = self._decrypt_enc_bytes(data, int(enc_seed), int(enc_len))
                with open(output_path, 'wb') as f:
                    f.write(decrypted_data)
            elif is_scrambled and scramble_seed and int(scramble_seed) != 0:
                # Fallback to the old grid-based descrambler
                self._descramble_and_save(data, int(scramble_seed), output_path)
            else:
                with open(output_path, 'wb') as f:
                    f.write(data)

    def _decrypt_enc_bytes(self, data: bytes, seed: int, length: int) -> bytes:
        # Kotlin equivalent of the Descrambler LCG logic:
        # Each byte in the scrambled data is XORed with (current_seed ushr 24) & 0xFF
        # and current_seed is updated using current_seed = current_seed * ENC_MULTIPLIER + ENC_INCREMENT
        state = seed & 0xFFFFFFFF
        decrypted = bytearray(data)
        
        limit = min(len(data), max(0, length))
        for idx in range(limit):
            state = (state * 1000005 + 1234567891) & 0xFFFFFFFF
            key_byte = (state >> 24) & 0xFF
            decrypted[idx] = data[idx] ^ key_byte
            
        return bytes(decrypted)

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

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        import os
        import concurrent.futures
        
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
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_download, enumerate(images)))
            
        return len(images)
