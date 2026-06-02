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
        self.base_url = "https://kagane.org"
        self.api_url = "https://yuzuki.kagane.org"
        self.cache_url = "https://akari.kagane.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/131.0.0.0',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/"
        }

    def _playwright_fetch_json(self, url: str, method: str = 'GET', data: dict = None, extra_headers: dict = None) -> dict:
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
                    user_agent=self.headers['User-Agent']
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                try:
                    page.goto("https://kagane.org/404", wait_until="domcontentloaded", timeout=15000)
                except:
                    pass
                
                # Aguarda se tiver desafio Cloudflare
                try:
                    page.wait_for_selector('h1, h2, div, p', timeout=10000 if headless else 180000)
                except:
                    if headless:
                        context.close()
                        return None
                        
                script = f"""
                async () => {{
                    const resp = await fetch("{url}", {{
                        method: "{method}",
                        headers: {json.dumps(extra_headers or {})},
                        body: {json.dumps(json.dumps(data)) if data else "null"}
                    }});
                    return await resp.text();
                }}
                """
                try:
                    result = page.evaluate(script)
                    context.close()
                    return json.loads(result)
                except Exception as e:
                    context.close()
                    if headless:
                        return None
                    raise e
                    
        res = run_browser(headless=True)
        if res is None:
            print("Kagane: Detectado bloqueio, abrindo janela visível...")
            res = run_browser(headless=False)
            
        return res

    def get_chapters(self, series_url):
        if "/book/" in series_url:
            return [series_url]

        parts = [p for p in series_url.split('/') if p]
        slug = parts[-1] if parts else ""
        
        api_endpoint = f"{self.api_url}/api/v2/series/{slug}"
        
        data = self._playwright_fetch_json(api_endpoint)
        if not data:
            raise Exception("Falha ao carregar informações da série Kagane (JSON vazio)")
            
        books = data.get('seriesBooks', [])
        chapters = []
        for book in books:
            book_id = book.get('uuid')
            chapters.append(f"{self.base_url}/series/{slug}/book/{book_id}")

        return list(reversed(chapters))

    def _get_drm_token(self, chapter_id: str) -> dict:
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
                    user_agent=self.headers['User-Agent']
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                
                page.goto("https://kagane.org/404", wait_until="domcontentloaded")
                
                script_full = """
                async (args) => {
                    const { chapterId } = args;
                    
                    // 1. Fetch Integrity
                    let intReq = await fetch("https://kagane.org/api/integrity", { method: 'POST' });
                    let intData = await intReq.json();
                    let integrityToken = intData.token;
                    
                    // 2. Fetch Certs
                    let binReq = await fetch("https://yuzuki.kagane.org/api/v2/static/bin.bin");
                    let binData = await binReq.arrayBuffer();
                    
                    let crtReq = await fetch("https://yuzuki.kagane.org/api/v2/static/crt.crt");
                    let crtData = await crtReq.arrayBuffer();
                    
                    // Utils
                    function arrayBufferToBase64(buffer) {
                        let binary = '';
                        let bytes = new Uint8Array(buffer);
                        let len = bytes.byteLength;
                        for (let i = 0; i < len; i++) {
                            binary += String.fromCharCode(bytes[i]);
                        }
                        return window.btoa(binary);
                    }
                    
                    function detectDRMSupport() {
                        return "WebKitMediaKeys" in window ? "fairplay" : "MediaKeys" in window && "function" == typeof navigator.requestMediaKeySystemAccess ? "widevine" : null;
                    }
                    
                    let widevine = detectDRMSupport() !== 'fairplay';
                    const g = widevine ? binData : crtData;
                    
                    // F hash logic
                    const fText = ":" + chapterId;
                    const encoder = new TextEncoder();
                    const data = encoder.encode(fText);
                    const fHashBuf = await crypto.subtle.digest('SHA-256', data);
                    const fBytes = new Uint8Array(fHashBuf).slice(0, 16);
                    
                    // PSSH logic
                    const eBase64 = "7e+LqXnWSs6jyCfc1R0h7Q==";
                    const eBytes = Uint8Array.from(atob(eBase64), c => c.charCodeAt(0));
                    
                    let iArray = new Uint8Array(2 + fBytes.length);
                    iArray[0] = 18;
                    iArray[1] = fBytes.length;
                    iArray.set(fBytes, 2);
                    
                    let sArray = new Uint8Array(4);
                    new DataView(sArray.buffer).setUint32(0, iArray.length, false);
                    
                    let innerBox = new Uint8Array(4 + eBytes.length + sArray.length + iArray.length);
                    innerBox.set(new Uint8Array([0,0,0,0]), 0);
                    innerBox.set(eBytes, 4);
                    innerBox.set(sArray, 4 + eBytes.length);
                    innerBox.set(iArray, 4 + eBytes.length + sArray.length);
                    
                    let outerSizeArray = new Uint8Array(4);
                    new DataView(outerSizeArray.buffer).setUint32(0, innerBox.length + 8, false);
                    
                    const psshHeader = encoder.encode("pssh");
                    let pssh = new Uint8Array(outerSizeArray.length + psshHeader.length + innerBox.length);
                    pssh.set(outerSizeArray, 0);
                    pssh.set(psshHeader, outerSizeArray.length);
                    pssh.set(innerBox, outerSizeArray.length + psshHeader.length);
                    
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
                    let tokenReq = await fetch(`https://yuzuki.kagane.org/api/v2/books/${chapterId}?is_datasaver=false`, {
                        method: 'POST',
                        headers: {
                            'x-integrity-token': integrityToken,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ challenge: challengeB64 })
                    });
                    
                    let tokenData = await tokenReq.json();
                    return tokenData;
                }
                """
                
                try:
                    result = page.evaluate(script_full, {'chapterId': chapter_id})
                    context.close()
                    return result
                except Exception as e:
                    context.close()
                    if headless:
                        return None
                    raise e

        res = run_browser(headless=True)
        if res is None:
            print("Kagane: Detectado bloqueio no DRM, abrindo janela visível...")
            res = run_browser(headless=False)
            
        return res

    def get_chapter_images(self, chapter_url):
        parts = [p for p in chapter_url.split('/') if p]
        chapter_id = parts[-1] if parts else ""
        
        if not chapter_id:
            raise Exception("Invalid chapter URL")
            
        challenge_data = self._get_drm_token(chapter_id)
        if not challenge_data or 'accessToken' not in challenge_data:
            raise Exception(f"Falha ao gerar DRM challenge, resposta inválida: {challenge_data}")
            
        access_token = challenge_data.get('accessToken')
        cache_url = challenge_data.get('cacheUrl', self.cache_url)
        pages = challenge_data.get('pages', [])
        
        images = []
        for page in pages:
            page_uuid = page.get('pageUuid')
            if page_uuid:
                img_url = f"{cache_url}/api/v2/books/file/{chapter_id}/{page_uuid}?token={access_token}&is_datasaver=false"
                images.append(img_url)
                
        return images
