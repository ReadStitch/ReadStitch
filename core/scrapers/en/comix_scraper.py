import time
import re
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from core.utils.uc_manager import get_cf_session, get_uc_driver

class ComixScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    @property
    def name(self) -> str:
        return "Comix.to"
        
    def _inject_interceptor(self, driver):
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': """
                window.__interceptedImages = null;
                window.__interceptedChapters = [];
                window.__chaptersSeen = new Set();
                window.__chaptersHasNext = true;
                
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
                                
                                if (parsed.result && parsed.result.items && Array.isArray(parsed.result.items)) {
                                    const items = parsed.result.items;
                                    const meta = parsed.result.meta || parsed.result.pagination || {};
                                    const page = meta.page || 1;
                                    const lastPage = meta.lastPage || meta.last_page || page;
                                    const hasNext = meta.hasNext || page < lastPage;
                                    
                                    if (!window.__chaptersSeen.has(page)) {
                                        window.__chaptersSeen.add(page);
                                        window.__interceptedChapters = window.__interceptedChapters.concat(items);
                                        if (!hasNext) {
                                            window.__chaptersHasNext = false;
                                        }
                                    }
                                }
                            }
                        } catch (e) {}
                        return parsed;
                    }
                });
                
                const originalFetch = window.fetch;
                window.fetch = async function(...args) {
                    let url = '';
                    if (typeof args[0] === 'string') {
                        url = args[0];
                    } else if (args[0] && typeof args[0] === 'object' && 'url' in args[0]) {
                        url = args[0].url;
                    }

                    if (url && url.includes('/chapters') && url.includes('limit=')) {
                        window.__chaptersApiUrl = url;
                        if (args.length > 1) {
                            window.__chaptersApiHeaders = args[1];
                        }
                    }

                    const response = await originalFetch.apply(this, args);
                    const clone = response.clone();
                    clone.json().then(parsed => {
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
                                
                                if (parsed.result && parsed.result.items && Array.isArray(parsed.result.items)) {
                                    const items = parsed.result.items;
                                    const meta = parsed.result.meta || parsed.result.pagination || {};
                                    const page = meta.page || 1;
                                    const lastPage = meta.lastPage || meta.last_page || page;
                                    const hasNext = meta.hasNext || page < lastPage;
                                    
                                    if (!window.__chaptersSeen.has(page)) {
                                        window.__chaptersSeen.add(page);
                                        window.__interceptedChapters = window.__interceptedChapters.concat(items);
                                        if (!hasNext) {
                                            window.__chaptersHasNext = false;
                                        }
                                    }
                                }
                            }
                        } catch(e) {}
                    }).catch(e => {});
                    return response;
                };
            """
        })

    def _fetch_rendered_chapters(self, url: str) -> dict:
        driver = get_uc_driver()
        self._inject_interceptor(driver)
        
        # O get_cf_session já garante que o Cloudflare foi passado.
        session = get_cf_session(url)
        time.sleep(4)
        
        api_chapters = []
        
        # Tentar ler os capítulos interceptados via script
        try:
            # Rolar e clicar em Load More/Next para carregar todos os capítulos na interceptação
            try:
                retries = 0
                page_count = 1
                while True:
                    has_next_flag = driver.execute_script("return window.__chaptersHasNext;")
                    if has_next_flag is False:
                        break
                        
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                    
                    clicked = driver.execute_script(f"""
                        let page = {page_count};
                        const buttons = [...document.querySelectorAll('.mchap-foot button')]
                            .filter(button => !button.disabled);
                        let nextBtn = buttons.find(button => {{
                            const label = [
                                button.getAttribute('aria-label'),
                                button.getAttribute('title'),
                                button.textContent
                            ].filter(Boolean).join(' ');
                            return /\\bnext\\b/i.test(label);
                        }}) || buttons.find(button => Number(button.textContent?.trim()) === page + 1);
                        
                        if (nextBtn) {{
                            nextBtn.click();
                            return true;
                        }}
                        return false;
                    """)
                    if not clicked:
                        retries += 1
                        if retries >= 15:
                            break
                        time.sleep(1.5)
                        continue
                        
                    retries = 0
                    page_count += 1
                    time.sleep(1.5)
            except Exception as e:
                pass

            items = driver.execute_script("return window.__interceptedChapters;")
            
            if items:
                for item in items:
                    url_path = item.get('url', '')
                    num = item.get('number', 0)
                    
                    group = item.get('group', {})
                    group_name = group.get('name', 'Padrão') if isinstance(group, dict) else 'Padrão'
                    
                    if url_path:
                        # Ignorar itens que são na verdade mangás relacionados (normalmente não possuem 'chapter-' na URL e o num é 0)
                        if not num and 'chapter-' not in url_path.lower():
                            continue
                            
                        full_link = f"https://comix.to/{url_path.lstrip('/')}"
                        api_chapters.append({
                            'num': float(num) if num else 0.0,
                            'url': full_link,
                            'group': group_name
                        })
        except Exception as e:
            print("Comix: Erro lendo capítulos interceptados:", e)
            
        # Fallback to HTML se a interceptação falhar
        if not api_chapters:
            page_count = 1
            while True:
                print(f"Lendo página {page_count} dos capítulos...")
                html = driver.page_source
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
                    retries = 0
                    while True:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(0.5)
                        
                        has_next = driver.execute_script(f"""
                            let btns = Array.from(document.querySelectorAll('button, a'));
                            
                            let btn = btns.find(b => {{
                                if (b.style.display === 'none') return false;
                                let disabled = b.disabled || b.classList.contains('disabled') || b.getAttribute('aria-disabled') === 'true';
                                if (disabled) return false;
                                
                                return (b.textContent && b.textContent.toLowerCase().trim() === 'load more') || 
                                       (b.textContent && b.textContent.toLowerCase().trim() === 'show more') || 
                                       (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('next')) ||
                                       (b.textContent && b.textContent.toLowerCase().includes('next page'));
                            }});
                            
                            if (!btn) {{
                                let targetPage = {page_count + 1};
                                btn = btns.find(b => b.textContent && b.textContent.trim() === String(targetPage) && b.style.display !== 'none');
                            }}
                            
                            if (btn) {{
                                btn.click();
                                return true;
                            }}
                            return false;
                        """)
                        if not has_next:
                            retries += 1
                            if retries >= 15:
                                break
                            time.sleep(1.5)
                            continue
                        
                        retries = 0
                        time.sleep(1.5)
                        page_count += 1
                        break
                        
                    if not has_next:
                        break
                except Exception:
                    break
                    
        # Remove duplicates by URL but keep highest number/cleanest data
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
        groups_dict = self._fetch_rendered_chapters(series_url)
        if not groups_dict:
            raise Exception("O ChromeDriver não encontrou capítulos. O Cloudflare pode ter bloqueado ou a página não carregou.")
        return groups_dict

    def get_chapters(self, series_url: str) -> list[str]:
        groups = self.get_chapter_groups(series_url)
        all_chaps = []
        for chaps in groups.values():
            all_chaps.extend(chaps)
        return all_chaps

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        driver = get_uc_driver()
        self._inject_interceptor(driver)
        
        session = get_cf_session(chapter_url)
        time.sleep(3)
        
        api_images = []
        
        # Try to get the intercepted images from the browser JS context
        try:
            pages_data = driver.execute_script("return window.__interceptedImages;")
            
            if pages_data:
                if isinstance(pages_data, dict):
                    base_url = pages_data.get('baseUrl', '').rstrip('/')
                    for index, item in enumerate(pages_data.get('items', [])):
                        u = item.get('url', '')
                        if u:
                            full_url = u if u.startswith('http') else f"{base_url}/{u.lstrip('/')}"
                            is_v3 = item.get('s') == 1 or "?v3" in full_url
                            
                            if is_v3:
                                if "?v3" not in full_url:
                                    full_url += "?v3"
                            else:
                                is_legacy_scramble = (index + 1) % 4 == 0
                                if is_legacy_scramble:
                                    full_url += "#scrambled"
                                    
                            api_images.append(full_url)
                elif isinstance(pages_data, list):
                    for index, item in enumerate(pages_data):
                        u = item.get('url', '')
                        if u:
                            full_url = u
                            is_v3 = item.get('s') == 1 or "?v3" in full_url
                            
                            if is_v3:
                                if "?v3" not in full_url:
                                    full_url += "?v3"
                            else:
                                is_legacy_scramble = (index + 1) % 4 == 0
                                if is_legacy_scramble:
                                    full_url += "#scrambled"
                                    
                            api_images.append(full_url)
        except Exception as e:
            print("Erro ao coletar window.__interceptedImages:", e)
            
        if api_images:
            # Salvar cookies para baixar no request normal depois
            self._uc_cookies = session.cookies.get_dict()
            self._uc_ua = session.headers.get('User-Agent')
            return api_images
            
        # FALLBACK: O Comix carrega as imagens via scroll (lazy load)
        print("Interceptação JSON falhou. Usando scroll manual...")
        for _ in range(80):
            driver.execute_script("window.scrollBy(0, 1500)")
            time.sleep(0.25)
            is_bottom = driver.execute_script("return window.scrollY + window.innerHeight >= document.body.scrollHeight;")
            if is_bottom:
                time.sleep(1)
                break
                    
        time.sleep(1.5)
        
        # Coletar as imagens renderizadas
        try:
            images = driver.execute_script('''
                const imgs = Array.from(document.querySelectorAll('img'));
                return imgs.map(img => img.getAttribute('data-src') || img.getAttribute('data-srcset') || img.src || img.getAttribute('src')).filter(src => {
                    if (!src) return false;
                    const low = src.toLowerCase();
                    // Ignore small placeholders/avatars/icons
                    if (low.includes('avatar') || low.includes('logo') || low.includes('icon') || low.includes('profile')) return false;
                    return low.includes('.jpg') || low.includes('.png') || low.includes('.jpeg') || low.includes('.webp') || src.startsWith('data:image');
                });
            ''')
        except Exception:
            images = []
            
        if not images and not api_images:
            raise Exception("O ChromeDriver não encontrou as imagens. O capítulo pode não ter carregado corretamente.")
            
        self._uc_cookies = session.cookies.get_dict()
        self._uc_ua = session.headers.get('User-Agent')
            
        # Filtrar duplicatas mantendo a ordem
        seen = set()
        ordered = []
        for img in images:
            if img not in seen:
                seen.add(img)
                ordered.append(img)
                
        return ordered

    def download_image(self, url, output_path):
        import requests
        from urllib.parse import urlparse
        
        is_scrambled = url.endswith("#scrambled")
        clean_url = url.split("#")[0]
        
        headers = self.headers.copy()
        
        if hasattr(self, '_uc_ua') and self._uc_ua:
            headers['User-Agent'] = self._uc_ua
            
        cookies = {}
        if hasattr(self, '_uc_cookies') and self._uc_cookies:
            cookies = self._uc_cookies
            
        headers['Referer'] = 'https://comix.to/'
        headers['Accept'] = 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        
        parsed = urlparse(clean_url)
        base_host = urlparse(getattr(self, 'baseUrl', 'https://comix.to')).netloc
        
        if parsed.netloc and not parsed.netloc.endswith(base_host) and not is_scrambled:
            if 'Origin' in headers:
                del headers['Origin']
        else:
            headers['Origin'] = 'https://comix.to'
        
        res = requests.get(clean_url, headers=headers, cookies=cookies)
        res.raise_for_status()
        data = res.content
        
        raw_scramble_seed = res.headers.get("x-scramble-seed")
        raw_scramble_grid = res.headers.get("x-scramble-grid")
        raw_scramble_algo = res.headers.get("x-scramble-algo")
        raw_scramble_hash = res.headers.get("x-scramble-hash")
        raw_enc_seed = res.headers.get("x-enc-seed")
        raw_enc_algo = res.headers.get("x-enc-algo")
        enc_len = res.headers.get("x-enc-len")
        
        enc_seed_val = int(raw_enc_seed) if raw_enc_seed and raw_enc_seed.lstrip('-').isdigit() else None
        enc_len_val = int(enc_len) if enc_len and enc_len.lstrip('-').isdigit() else None
        scramble_seed_val = int(raw_scramble_seed) if raw_scramble_seed and raw_scramble_seed.lstrip('-').isdigit() else None
        scramble_hash_val = self._decode_scramble_hash(raw_scramble_hash)
        
        needs_xor = enc_seed_val is not None and enc_seed_val != 0 and enc_len_val is not None
        should_descramble_grid = (raw_scramble_grid == "5x5" and
                                 raw_scramble_algo in (None, "1", "2", "3") and
                                 scramble_seed_val is not None and scramble_seed_val != 0)
                                 
        if not needs_xor and not should_descramble_grid and not (is_scrambled and scramble_seed_val):
            with open(output_path, 'wb') as f:
                f.write(data)
            return

        final_bytes = data
        if needs_xor:
            final_bytes = self._decode_encoded_bytes(data, enc_seed_val, enc_len_val, raw_enc_algo)
            
        if should_descramble_grid or (is_scrambled and scramble_seed_val):
            seed = (scramble_seed_val ^ scramble_hash_val) if should_descramble_grid else scramble_seed_val
            algo = raw_scramble_algo if should_descramble_grid else None
            self._descramble_and_save(final_bytes, seed, algo, output_path)
        else:
            with open(output_path, 'wb') as f:
                f.write(final_bytes)

    def _decode_scramble_hash(self, hash_str):
        if not hash_str: return 0
        h = hash_str.strip()
        if h == "03632": return 58414
        if h == "02900": return 117532
        return 0

    def _decode_encoded_bytes(self, data: bytes, seed: int, length: int, algo: str) -> bytes:
        if algo != "2":
            return self._decode_with_lcg(data, seed, length)
            
        candidates = [
            self._decode_with_xorshift(data, seed | 1, length, False),
            self._decode_with_xorshift(data, seed, length, False),
            self._decode_with_xorshift(data, seed | 1, length, True),
            self._decode_with_lcg(data, seed, length),
        ]
        
        for cand in candidates:
            if self._has_image_signature(cand):
                return cand
        return candidates[0]
        
    def _has_image_signature(self, b: bytes) -> bool:
        if len(b) < 12: return False
        if b[0:4] == b'RIFF' and b[8:12] == b'WEBP': return True
        if b[0] == 0xFF and b[1] == 0xD8: return True
        if b[0:4] == b'\x89PNG': return True
        return False
        
    def _decode_with_xorshift(self, data: bytes, initial_state: int, length: int, high_byte: bool) -> bytes:
        result = bytearray(data)
        state = initial_state & 0xFFFFFFFF
        limit = min(len(data), length)
        
        for i in range(limit):
            state ^= (state << 13) & 0xFFFFFFFF
            state ^= (state >> 17) & 0xFFFFFFFF
            state ^= (state << 5) & 0xFFFFFFFF
            
            key = (state >> 24) if high_byte else (state & 0xFF)
            result[i] = result[i] ^ key
            
        return bytes(result)
        
    def _decode_with_lcg(self, data: bytes, seed: int, length: int) -> bytes:
        state = seed & 0xFFFFFFFF
        result = bytearray(data)
        limit = min(len(data), length)
        for i in range(limit):
            state = (state * 1000005 + 1234567891) & 0xFFFFFFFF
            result[i] = result[i] ^ ((state >> 24) & 0xFF)
        return bytes(result)

    def _descramble_and_save(self, image_bytes, seed, algo, output_path):
        from PIL import Image
        from io import BytesIO
        
        GRID_COLS = 5
        GRID_ROWS = 5
        NUM_TILES = GRID_COLS * GRID_ROWS
        
        if algo == "3":
            order = self._build_order_xorshift(seed, NUM_TILES)
        else:
            order = self._build_order_lcg(seed, NUM_TILES)
            
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGBA")
            width, height = img.size
            tile_w = width // GRID_COLS
            tile_h = height // GRID_ROWS
            
            output = Image.new("RGBA", (width, height))
            
            for dst_idx in range(NUM_TILES):
                src_idx = order[dst_idx]
                
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
                
                tile = img.crop(src_rect)
                
                dst_x = dst_col * tile_w
                dst_y = dst_row * tile_h
                
                output.paste(tile, (dst_x, dst_y))
                
            if output.mode == "RGBA":
                bg = Image.new("RGB", output.size, (255, 255, 255))
                bg.paste(output, mask=output.split()[3])
                output = bg
                
            output.save(output_path, format="JPEG", quality=90)
            
    def _build_order_xorshift(self, seed: int, n: int) -> list:
        arr = list(range(n))
        state = (seed | 1) & 0xFFFFFFFF
        for i in range(n - 1, 0, -1):
            state ^= (state << 13) & 0xFFFFFFFF
            state ^= (state >> 17) & 0xFFFFFFFF
            state ^= (state << 5) & 0xFFFFFFFF
            
            j = state % (i + 1)
            arr[i], arr[j] = arr[j], arr[i]
            
        inverse = [0] * n
        for i, val in enumerate(arr):
            inverse[val] = i
        return inverse

    def _build_order_lcg(self, seed: int, n: int) -> list:
        arr = list(range(n))
        state = seed & 0xFFFFFFFF
        for i in range(n - 1, 0, -1):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            j = state % (i + 1)
            arr[i], arr[j] = arr[j], arr[i]
            
        inverse = [0] * n
        for i, val in enumerate(arr):
            inverse[val] = i
        return inverse

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
