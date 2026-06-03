import os
import json
import urllib.request
import hashlib
import base64
import time
from .base_scraper import BaseScraper

class KaganeScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.domain_tld = "org"
        self.base_url = "https://kagane.org"
        self.api_url = "https://yuzuki.kagane.org"
        self.cache_url = "https://akari.kagane.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/"
        }
        self.cookies = []

    def _update_domain(self, url: str):
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc
        if domain and 'kagane' in domain:
            tld = domain.split('.')[-1]
            self.domain_tld = tld
            self.base_url = f"https://kagane.{tld}"
            self.api_url = f"https://yuzuki.kagane.{tld}"
            self.cache_url = f"https://akari.kagane.{tld}"
            self.headers['Origin'] = self.base_url
            self.headers['Referer'] = f"{self.base_url}/"

    def _playwright_fetch_json(self, url: str, method: str = 'GET', data: dict = None, extra_headers: dict = None) -> dict:
        from playwright.sync_api import sync_playwright
        import os
        import json
        
        # Como o urllib nativo está sendo bloqueado pelo Cloudflare de qualquer forma,
        # navegamos diretamente para a URL da API usando o Chrome real (CDP).
        # Isso dribla as proteções de CORS e pega a resposta diretamente da tela.
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_browser")
        chrome_process = self._launch_chrome_cdp(profile_dir, headless=False)
        
        def _do_fetch():
            from playwright.sync_api import sync_playwright
            import json
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                
                try:
                    print(f"Kagane: Carregando lista de capítulos... (Passe pelo Cloudflare se aparecer)")
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    for _ in range(60):
                        if page.is_closed(): break
                        try:
                            title = page.title()
                            if 'Just a moment' not in title and 'Cloudflare' not in title:
                                break
                        except: pass
                        page.wait_for_timeout(1000)
                    
                    page.wait_for_timeout(2000)
                    
                    if not page.is_closed():
                        script = f"""
                        async () => {{
                            let req = await fetch("{url}");
                            return await req.text();
                        }}
                        """
                        try:
                            res_text = page.evaluate(script)
                            res = json.loads(res_text)
                            browser.close()
                            return res
                        except Exception as e:
                            print(f"Kagane: Erro no fetch interno: {e}")
                            
                except Exception as e:
                    print(f"Kagane: Erro ao carregar API {url}: {e}")
                    
                try:
                    browser.close()
                except: pass
                return None
                
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

    def get_chapters(self, series_url):
        self._update_domain(series_url)
        if "/book/" in series_url:
            return [series_url]

        parts = [p for p in series_url.split('/') if p]
        slug = parts[-1] if parts else ""
        
        api_endpoint = f"{self.api_url}/api/v2/series/{slug}"
        
        data = self._playwright_fetch_json(api_endpoint)
        if not data:
            raise Exception("Falha ao carregar informações da série Kagane (JSON vazio)")
            
        books = data.get('series_books', []) or data.get('seriesBooks', [])
        chapters = []
        for book in books:
            book_id = book.get('book_id') or book.get('uuid')
            chapter_no = book.get('chapter_no', '')
            url = f"{self.base_url}/series/{slug}/book/{book_id}"
            if chapter_no:
                url += f"?chapter={chapter_no}"
            chapters.append(url)

        return list(reversed(chapters))

    def _launch_chrome_cdp(self, profile_dir, headless=False):
        import subprocess
        import time
        
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            "--user-data-dir=" + profile_dir,
            "--no-first-run",
            "--no-default-browser-check"
        ]
        if headless:
            cmd.append("--headless=new")
            
        process = subprocess.Popen(cmd)
        time.sleep(3) # Aguarda porta abrir
        return process



    def _get_drm_token(self, chapter_id: str) -> dict:
        from playwright.sync_api import sync_playwright
        
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_browser")
        os.makedirs(profile_dir, exist_ok=True)
        
        def run_browser(headless):
            chrome_process = self._launch_chrome_cdp(profile_dir, headless=headless)
            
            def _do_drm():
                from playwright.sync_api import sync_playwright
                import json
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp("http://localhost:9222")
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else context.new_page()
                
                    try:
                        page.goto(f"{self.base_url}/404", wait_until="domcontentloaded", timeout=15000)
                    
                        # Se não estiver no modo invisível, aguarda o Cloudflare passar antes de injetar o script
                        if not headless:
                            print("Kagane: DRM solicitando resolução de Cloudflare. Por favor resolva...")
                            for _ in range(60):
                                if not page.is_closed():
                                    try:
                                        title = page.evaluate("() => document.title")
                                        if 'Just a moment' not in title and 'Cloudflare' not in title:
                                            break
                                    except: pass
                                    page.wait_for_timeout(1000)
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except: pass
                        page.wait_for_timeout(2000)
                    except:
                        pass
                    
                    script_full = """
                    async (args) => {
                        const { chapterId, isHeadless } = args;
                    
                        let integrityToken = null;
                        let attempts = 0;
                        while (true) {
                            try {
                                let intReq = await fetch("https://kagane.to/api/integrity", { method: 'POST' });
                                let intText = await intReq.text();
                    
                                // Se retornou JSON válido com 'token', saímos do loop!
                                if (intText.includes('"token"')) {
                                    let intData = JSON.parse(intText);
                                    integrityToken = intData.token;
                                    break;
                                }
                            } catch(e) {}
                    
                            attempts++;
                            if (isHeadless && attempts >= 3) {
                                throw new Error("Cloudflare block detected in headless mode");
                            }
                    
                            // Espera 2 segundos antes de tentar de novo
                            await new Promise(r => setTimeout(r, 2000));
                        }
                    
                        // Tenta requisição sem DRM primeiro (Nova API Kagane)
                        let directReq = await fetch(`https://yuzuki.kagane.to/api/v2/books/${chapterId}?is_datasaver=false`, {
                            method: 'POST',
                            headers: {
                                'x-integrity-token': integrityToken,
                                'Content-Type': 'application/json'
                            },
                            body: "{}"
                        });
                        
                        if (directReq.ok) {
                            return await directReq.text();
                        }
                    
                        // Continua com o resto do DRM agora que temos o token
                        let binReq = await fetch("https://kagane.to/api/v2/static/bin.bin");
                        let binData = await binReq.arrayBuffer();
                        let crtReq = await fetch("https://kagane.to/api/v2/static/crt.crt");
                        let crtData = await crtReq.arrayBuffer();
                    
                        function detectDRMSupport() {
                            return "WebKitMediaKeys" in window ? "fairplay" : "MediaKeys" in window && "function" == typeof navigator.requestMediaKeySystemAccess ? "widevine" : null;
                        }
                    
                        function base64ToArrayBuffer(base64) {
                            var binaryString = atob(base64);
                            var bytes = new Uint8Array(binaryString.length);
                            for (var i = 0; i < binaryString.length; i++) {
                                bytes[i] = binaryString.charCodeAt(i);
                            }
                            return bytes.buffer;
                        }
                    
                        function arrayBufferToBase64(buffer) {
                            let binary = '';
                            let bytes = new Uint8Array(buffer);
                            for (let i = 0; i < bytes.byteLength; i++) {
                                binary += String.fromCharCode(bytes[i]);
                            }
                            return window.btoa(binary);
                        }
                    
                        let widevine = detectDRMSupport() !== 'fairplay';
                        const g = widevine ? binData : crtData;
                    
                        const fText = ':' + chapterId;
                        const encoder = new TextEncoder();
                        const data = encoder.encode(fText);
                        const fHashBuf = await crypto.subtle.digest('SHA-256', data);
                        const fBytes = new Uint8Array(fHashBuf).slice(0, 16);
                    
                        const eBase64 = '7e+LqXnWSs6jyCfc1R0h7Q==';
                        const eBytes = Uint8Array.from(atob(eBase64), c => c.charCodeAt(0));
                    
                        let iArray = new Uint8Array(2 + fBytes.length);
                        iArray[0] = 18; iArray[1] = fBytes.length; iArray.set(fBytes, 2);
                    
                        let sArray = new Uint8Array(4);
                        new DataView(sArray.buffer).setUint32(0, iArray.length, false);
                    
                        let innerBox = new Uint8Array(4 + eBytes.length + sArray.length + iArray.length);
                        innerBox.set(new Uint8Array([0,0,0,0]), 0); innerBox.set(eBytes, 4);
                        innerBox.set(sArray, 4 + eBytes.length); innerBox.set(iArray, 4 + eBytes.length + sArray.length);
                    
                        let outerSizeArray = new Uint8Array(4);
                        new DataView(outerSizeArray.buffer).setUint32(0, innerBox.length + 8, false);
                    
                        const psshHeader = encoder.encode('pssh');
                        let pssh = new Uint8Array(outerSizeArray.length + psshHeader.length + innerBox.length);
                        pssh.set(outerSizeArray, 0); pssh.set(psshHeader, outerSizeArray.length); pssh.set(innerBox, outerSizeArray.length + psshHeader.length);
                    
                        let t = widevine ? await navigator.requestMediaKeySystemAccess("com.widevine.alpha", [{
                            initDataTypes: ["cenc"],
                            audioCapabilities: [],
                            videoCapabilities: [{
                                contentType: 'video/mp4; codecs="avc1.42E01E"'
                            }]
                        }]) : await navigator.requestMediaKeySystemAccess("com.apple.fps", [{
                            initDataTypes: ["skd"],
                            audioCapabilities: [{
                                contentType: 'audio/mp4; codecs="mp4a.40.2"'
                            }],
                            videoCapabilities: [{
                                contentType: 'video/mp4; codecs="avc1.42E01E"'
                            }]
                        }]);
                    
                        let eKey = await t.createMediaKeys();
                        await eKey.setServerCertificate(g);
                        let video = widevine ? null : document.createElement("video");
                        if (video) {
                            video.style.display = "none";
                            document.body.appendChild(video);
                            await video.setMediaKeys(eKey);
                        }
                    
                        let n = eKey.createSession();
                        let iPromise = new Promise((resolve, reject) => {
                            function onMessage(event) {
                                n.removeEventListener("message", onMessage);
                                if (video) { document.body.removeChild(video); }
                                resolve(event.message);
                            }
                            function onError() {
                                n.removeEventListener("error", onError);
                                reject(new Error("Failed to generate license challenge"));
                            }
                            n.addEventListener("message", onMessage);
                            n.addEventListener("error", onError);
                        });
                    
                        if (widevine) {
                            await n.generateRequest("cenc", pssh.buffer);
                        } else {
                            let c = Array.from(fBytes).map(t => t.toString(16).padStart(2, "0")).join("");
                            let d = JSON.stringify({
                                uri: "skd://" + c,
                                assetId: chapterId,
                            });
                            await n.generateRequest("skd", encoder.encode(d));
                        }
                    
                        let o = await iPromise;
                        let challengeB64 = arrayBufferToBase64(o);
                    
                        // Final API Call to get token
                        let tokenReq = await fetch(`https://yuzuki.kagane.to/api/v2/books/${chapterId}?is_datasaver=false`, {
                            method: 'POST',
                            headers: {
                                'x-integrity-token': integrityToken,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ challenge: challengeB64 })
                        });
                    
                        return await tokenReq.text();
                    }
                    """
                    script_full = script_full.replace("kagane.to", f"kagane.{self.domain_tld}")
                    
                    # Tenta executar o DRM. Se o Cloudflare recarregar a página no meio, ele tenta de novo.
                    for attempt in range(5):
                        try:
                            result = page.evaluate(script_full, {'chapterId': chapter_id, 'isHeadless': headless})
                            browser.close()
                            return json.loads(result)
                        except Exception as e:
                            if "Execution context was destroyed" in str(e) or "Target page, context or browser has been closed" in str(e):
                                page.wait_for_timeout(3000)
                                continue
                            browser.close()
                            if headless:
                                return None
                            raise e
                            
                    # Se falhar 5 vezes
                    browser.close()
                    if headless: return None
                    raise Exception("Falha ao obter DRM após várias tentativas.")
                    
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_do_drm)
                    return future.result()
            finally:
                import subprocess
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(chrome_process.pid)], capture_output=True)
                except:
                    pass
                chrome_process.terminate()

        res = run_browser(headless=True)
        if res is None:
            print("Kagane: Detectado bloqueio no DRM, abrindo janela visível...")
            res = run_browser(headless=False)
            
        return res

    def get_chapter_images(self, chapter_url):
        self._update_domain(chapter_url)
        clean_url = chapter_url.split('?')[0]
        parts = [p for p in clean_url.split('/') if p]
        chapter_id = parts[-1] if parts else ""
        
        if not chapter_id:
            raise Exception("Invalid chapter URL")
            
        challenge_data = self._get_drm_token(chapter_id)
        if not challenge_data or ('accessToken' not in challenge_data and 'access_token' not in challenge_data):
            raise Exception(f"Falha ao gerar DRM challenge, resposta inválida: {challenge_data}")
            
        access_token = challenge_data.get('accessToken') or challenge_data.get('access_token')
        cache_url = challenge_data.get('cacheUrl') or challenge_data.get('cache_url') or self.cache_url
        is_new_api = 'manifest' in challenge_data and challenge_data['manifest'] is not None
        
        if is_new_api:
            pages = challenge_data.get('manifest', {}).get('pages', [])
        else:
            pages = challenge_data.get('pages', [])
            
        images = []
        for page in pages:
            # Pega o UUID novo ou velho
            page_uuid = page.get('page_id') or page.get('pageUuid') or page.get('uuid') or page.get('id')
            if page_uuid:
                if is_new_api:
                    ext = page.get('ext', 'jxl')
                    img_url = f"{cache_url}/api/v2/books/page/{chapter_id}/{page_uuid}.{ext}?token={access_token}&is_datasaver=false"
                else:
                    img_url = f"{cache_url}/api/v2/books/file/{chapter_id}/{page_uuid}?token={access_token}&is_datasaver=false"
                images.append(img_url)
                
        return images
