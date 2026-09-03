import os
import re
import json
import logging
import time
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

FETCH_PATCH = """
window._capturedImages = {};
window._captureOrder = [];
const _origFetch = window.fetch;
window.fetch = async function(...args) {
    const url = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url ? args[0].url : String(args[0]));
    const response = await _origFetch.apply(this, args);
    
    if (url.includes('image-loader.php') && response.ok) {
        try {
            const clone = response.clone();
            const buffer = await clone.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = '';
            const chunk = 8192;
            for (let i = 0; i < bytes.byteLength; i += chunk) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i+chunk, bytes.byteLength)));
            }
            const idx = window._captureOrder.length;
            window._capturedImages[url] = { idx, b64: btoa(binary), size: bytes.byteLength };
            window._captureOrder.push(url);
        } catch(e) { }
    }
    return response;
};
"""

class TiraninhaScraper(BaseScraper):
    """Scraper para Tiraninha usando Playwright para contornar proteções complexas."""

    @property
    def name(self):
        return "Tiraninha"

    def __init__(self):
        super().__init__()
        self.base_url = "https://tiraninha.world"

    def _xor_decrypt(self, data: bytes, key: str) -> bytes:
        if not key:
            return data
        v = bytearray(data)
        x_len = min(1024, len(v))
        key_bytes = key.encode('utf-8')
        key_len = len(key_bytes)
        for i in range(x_len):
            v[i] ^= key_bytes[i % key_len]
        return bytes(v)

    def login(self, email, password):
        """O login agora deve ser evitado se possivel, ou feito via GUI, 
        mas Tiraninha raramente exige login hard para ler capitulos abertos.
        Deixando compatibilidade caso seja chamado."""
        logger.info(f"[{self.name}] Função de login via API chamada (ignorada na v2)")
        return True

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos via HTTP simples...")
        try:
            req = Request(series_url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urlopen(req).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            raise Exception(f"Falha ao buscar página da série: {e}")

        all_chapters = []
        links = soup.find_all('a', class_='mc-chapter-link')
        if not links:
            links = soup.select('li.wp-manga-chapter a')
        for a in links:
            href = a.get('href', '').strip()
            if href and href not in all_chapters:
                all_chapters.append(href)
        
        # Paginação Ajax
        manga_id = None
        action_btn = soup.find('a', class_='wp-manga-action-button')
        if action_btn:
            manga_id = action_btn.get('data-post')
            
        if manga_id:
            import urllib.parse
            ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"
            offset = len(all_chapters)
            while True:
                data = urllib.parse.urlencode({
                    'action': 'load_more_chapters',
                    'manga_id': manga_id,
                    'offset': str(offset)
                }).encode('utf-8')
                try:
                    req_ajax = Request(ajax_url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded'})
                    resp_json = json.loads(urlopen(req_ajax).read().decode('utf-8'))
                    if not resp_json.get('success'): break
                    ajax_html = resp_json.get('data', {}).get('html', '')
                    if not ajax_html: break
                    
                    ajax_soup = BeautifulSoup(ajax_html, 'html.parser')
                    ajax_links = ajax_soup.find_all('a', class_='mc-chapter-link')
                    if not ajax_links:
                        ajax_links = ajax_soup.select('li.wp-manga-chapter a')
                        
                    found = False
                    for a in ajax_links:
                        href = a.get('href', '').strip()
                        if href and href not in all_chapters:
                            all_chapters.append(href)
                            found = True
                    if not found: break
                    offset += 12
                except Exception:
                    break

        all_chapters.reverse()
        return all_chapters

    def get_chapter_images(self, chapter_url):
        # Usado apenas para compatibilidade. A extração real ocorre no download_chapter.
        return ["gatekeeper_mode"]

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)
        
        logger.info(f"[{self.name}] Carregando página do capítulo...")
        
        # 1. Fetch chapter page to get the image script and chapter HTML
        try:
            req = Request(chapter_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            html = urlopen(req).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar página: {e}")
            return 0
            
        import concurrent.futures

        # Check for the new base64 canvas format
        pages_script = soup.find('script', string=re.compile(r'var\s+pages\s*=\s*\['))
        if pages_script:
            logger.info(f"[{self.name}] Novo formato detectado (base64 canvas)")
            match = re.search(r'var\s+pages\s*=\s*\[(.*?)\]', pages_script.string, re.DOTALL)
            if match:
                import base64
                
                paths_b64 = [p.strip().strip('"').strip("'") for p in match.group(1).split(',')]
                paths_b64 = [p for p in paths_b64 if p]
                
                try:
                    urls = [base64.b64decode(p).decode('utf-8') for p in paths_b64]
                except Exception as e:
                    logger.error(f"[{self.name}] Erro ao decodificar base64: {e}")
                    return 0
                
                logger.info(f"[{self.name}] Encontradas {len(urls)} imagens esperadas")
                
                def _download_simple(args):
                    idx, url = args
                    headers = {
                        "Accept": "*/*",
                        "Referer": chapter_url,
                        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    }
                    try:
                        img_req = Request(url, headers=headers)
                        img_data = urlopen(img_req).read()
                        
                        ext = "jpg"
                        if img_data.startswith(b'\x89PNG\r\n\x1a\n'):
                            ext = "png"
                        elif img_data.startswith(b'\xff\xd8\xff'):
                            ext = "jpg"
                        elif img_data.startswith(b'RIFF') and img_data[8:12] == b'WEBP':
                            ext = "webp"
                        elif img_data[4:8] == b'ftyp' and b'avif' in img_data[8:12]:
                            ext = "avif"
                        elif img_data.startswith(b'GIF87a') or img_data.startswith(b'GIF89a'):
                            ext = "gif"
                            
                        out_path = os.path.join(target_dir, f"{idx+1:03d}.{ext}")
                        with open(out_path, "wb") as f:
                            f.write(img_data)
                        logger.info(f"[{self.name}] Imagem {idx+1} salva.")
                        return True
                    except Exception as e:
                        logger.error(f"[{self.name}] Erro ao processar imagem {idx+1}: {e}")
                        return False

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = list(executor.map(_download_simple, enumerate(urls)))
                saved_count = sum(1 for r in results if r)
                logger.info(f"[{self.name}] Finalizado. Total salvo: {saved_count}")
                return saved_count
        
        # Fallback to the old gatekeeper logic
        logger.info(f"[{self.name}] Formato antigo detectado (gatekeeper)")
        
        # Extract proxyUrls
        proxy_script = soup.find('script', string=re.compile(r'_proxyUrls'))
        if not proxy_script:
            logger.error(f"[{self.name}] _proxyUrls e pages n\u00e3o encontrados na p\u00e1gina")
            return 0
        
        match = re.search(r'_proxyUrls\s*=\s*\[(.*?)\]', proxy_script.string, re.DOTALL)
        if not match:
            logger.error(f"[{self.name}] Regex falhou ao extrair _proxyUrls")
            return 0
            
        paths = [p.strip().strip('"').strip("'").replace('\\/', '/') for p in match.group(1).split(',')]
        paths = [p for p in paths if p]
        
        if not paths:
            logger.error(f"[{self.name}] Nenhuma imagem encontrada")
            return 0
            
        logger.info(f"[{self.name}] Encontradas {len(paths)} imagens esperadas")
        
        # 2. Get JWT token from gatekeeper
        timestamp = int(time.time() * 1000)
        gatekeeper_url = f"{self.base_url}/wp-content/themes/madara2/gatekeeper.php?t={timestamp}"
        
        gk_headers = {
            "Accept": "*/*",
            "Referer": chapter_url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            "X-Reader-Sec": "tiraninha-web"
        }
        
        try:
            gk_req = Request(gatekeeper_url, headers=gk_headers)
            gk_resp = urlopen(gk_req).read().decode('utf-8')
            gk_json = json.loads(gk_resp)
            token = gk_json.get('token')
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar gatekeeper: {e}")
            return 0
            
        if not token:
            logger.error(f"[{self.name}] Token n\u00e3o retornado pelo gatekeeper")
            return 0
            
        parts = token.split('.')
        if len(parts) < 2:
            logger.error(f"[{self.name}] Token JWT inv\u00e1lido")
            return 0
            
        xor_key = parts[1][4:20]
        logger.info(f"[{self.name}] Token obtido com sucesso. Chave XOR: {xor_key}")
        
        def _download_image(args):
            idx, img_path = args
            url = f"{self.base_url}{img_path}"
            
            headers = {
                "Accept": "*/*",
                "Referer": chapter_url,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                "X-Reader-Sec": "tiraninha-web",
                "X-Internal-XOR-Key": xor_key,
                "Cookie": f"lt_sec_val={token}; path=/"
            }
            
            try:
                img_req = Request(url, headers=headers)
                img_data = urlopen(img_req).read()
                
                decrypted = self._xor_decrypt(img_data, xor_key)
                
                ext = "jpg"
                if decrypted.startswith(b'\x89PNG\r\n\x1a\n'):
                    ext = "png"
                elif decrypted.startswith(b'\xff\xd8\xff'):
                    ext = "jpg"
                elif decrypted.startswith(b'RIFF') and decrypted[8:12] == b'WEBP':
                    ext = "webp"
                elif decrypted[4:8] == b'ftyp' and b'avif' in decrypted[8:12]:
                    ext = "avif"
                elif decrypted.startswith(b'GIF87a') or decrypted.startswith(b'GIF89a'):
                    ext = "gif"
                
                out_path = os.path.join(target_dir, f"{idx+1:03d}.{ext}")
                with open(out_path, "wb") as f:
                    f.write(decrypted)
                
                logger.info(f"[{self.name}] Imagem {idx+1} salva.")
                return True
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao processar imagem {idx+1}: {e}")
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_download_image, enumerate(paths)))
            
        saved_count = sum(1 for r in results if r)
        logger.info(f"[{self.name}] Finalizado. Total salvo: {saved_count}")
        return saved_count
