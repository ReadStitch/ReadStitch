import os
import re
import time
import logging
import json
import threading
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Lock global para evitar que o Playwright abra múltiplas instâncias no mesmo profile e corrompa/crushe a sessão
_comikey_browser_lock = threading.Lock()

class ComikeyScraper(BaseScraper):
    @property
    def name(self):
        return "Comikey"

    def __init__(self):
        super().__init__()
        self.base_url = "https://comikey.com"
        self._email = ""
        self._password = ""

    def _load_credentials(self):
        try:
            from core.services.settings_handler import SettingsHandler
            settings = SettingsHandler()
            self._email = settings.load("comikey_email", "")
            self._password = settings.load("comikey_password", "")
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar credenciais: {e}")


    def _fetch_with_playwright(self, url: str, force_visible: bool = False) -> dict:
        self._load_credentials()
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_comikey_browser")
        os.makedirs(profile_dir, exist_ok=True)
        
        def run_browser(headless):
            from playwright.sync_api import sync_playwright
            
            with _comikey_browser_lock:
                with sync_playwright() as p:
                    try:
                        args = ["--disable-blink-features=AutomationControlled", "--disable-infobars"]
                        if headless:
                            args.append("--headless=new")
                            
                        context = p.chromium.launch_persistent_context(
                            user_data_dir=profile_dir,
                            headless=False, # Usamos False nativo para forçar o Playwright a respeitar nossos args e compartilhar cookies
                            channel="chrome",
                            args=args
                        )
                        page = context.pages[0] if context.pages else context.new_page()

                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            time.sleep(5)
                            
                            html = page.content()
                            html_lower = html.lower()
                            
                            # Verifica se o capítulo está bloqueado pedindo login
                            if "log in" in html_lower or "sign in" in html_lower or "auth/login" in html_lower:
                                if headless:
                                    context.close()
                                    return None # Falhou, vai para o plano visível
                                
                                if self._email and self._password:
                                    logger.info(f"[{self.name}] Capítulo exigiu login. Realizando autenticação...")
                                    import urllib.parse
                                    parsed_url = urllib.parse.urlparse(url)
                                    login_url = f"{parsed_url.scheme}://{parsed_url.netloc}/auth/login/"
                                    page.goto(login_url, wait_until="domcontentloaded")
                                    time.sleep(2)
                                    if "login" in page.url:
                                        try:
                                            page.fill("input[name='login']", self._email, timeout=3000)
                                            page.fill("input[name='password']", self._password, timeout=3000)
                                            page.click("button[type='submit']", timeout=3000)
                                            for _ in range(60):
                                                if "login" not in page.url:
                                                    break
                                                time.sleep(1)
                                            time.sleep(2)
                                        except Exception as e:
                                            logger.warning(f"Erro no auto-login: {e}")
                                    
                                    # Volta para o capítulo após o login
                                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                                    time.sleep(5)
                                    html = page.content()

                            cf_blocked = False
                            try:
                                title = page.title().strip()
                                if "Just a moment" in title or "Cloudflare" in title:
                                    cf_blocked = True
                            except: pass
                            
                            if headless and cf_blocked:
                                context.close()
                                return None

                            images_data = []
                            # Somente espera imagens e força o scroll se for uma página de leitura (capítulo)
                            if "/read/" in url or "episode" in url.lower() or "chapter" in url.lower():
                                try:
                                    # A página usa class 'page-img' e imagens no formato BLOB/Canvas (Eles usam DRM em canvas na maioria das vezes)
                                    page.wait_for_selector(".page-img, canvas", timeout=15000)
                                    
                                    # Rolar a página lentamente para forçar o carregamento de imagens preguiçosas (lazy loading) e o preenchimento dos SRCs
                                    page.evaluate('''() => {
                                        return new Promise((resolve) => {
                                            let totalHeight = 0;
                                            let distance = 500;
                                            let timer = setInterval(() => {
                                                let scrollHeight = document.body.scrollHeight;
                                                window.scrollBy(0, distance);
                                                totalHeight += distance;
                                                if(totalHeight >= scrollHeight){
                                                    clearInterval(timer);
                                                    resolve();
                                                }
                                            }, 100);
                                        });
                                    }''')

                                    time.sleep(3) # Give it some time to draw on canvas and blobs after scrolling
                                    
                                    # Try to extract via JS Fetch first
                                    js_extracted = page.evaluate('''async () => {
                                        let results = [];
                                        
                                        const blobToBase64 = async (blobUrl) => {
                                            try {
                                                const response = await fetch(blobUrl);
                                                const blob = await response.blob();
                                                return new Promise((resolve, reject) => {
                                                    const reader = new FileReader();
                                                    reader.onloadend = () => resolve(reader.result);
                                                    reader.onerror = reject;
                                                    reader.readAsDataURL(blob);
                                                });
                                            } catch (e) { return null; }
                                        };

                                        let imgs = document.querySelectorAll('.page-img, .reader-image img');
                                        for (let img of imgs) {
                                            if (!img.src) continue;
                                            if (img.src.startsWith('blob:')) {
                                                let b64 = await blobToBase64(img.src);
                                                if (b64) results.push({type: 'base64', src: b64});
                                            } else {
                                                results.push({type: 'url', src: img.src});
                                            }
                                        }
                                        
                                        document.querySelectorAll('canvas').forEach(cvs => {
                                            try {
                                                results.push({type: 'base64', src: cvs.toDataURL('image/jpeg', 0.95)});
                                            } catch(e) {}
                                        });
                                        return results;
                                    }''')
                                    
                                    if js_extracted:
                                        images_data.extend(js_extracted)
                                        
                                    # Se o JS falhou em extrair os blobs (Retornou lista vazia ou len = 0), vamos tirar screenshot dos elementos HTML das páginas
                                    if len(images_data) == 0:
                                        logger.info(f"[{self.name}] Extração via JS falhou, possivelmente devido a DRM/CORS de Blobs. Tentando capturar elementos visuais...")
                                        
                                        # Esconder UI elements dinamicamente (qualquer barra fixa ou sticky que sobreponha a tela)
                                        page.evaluate('''() => {
                                            document.querySelectorAll('*').forEach(el => {
                                                try {
                                                    let style = window.getComputedStyle(el);
                                                    if (style.position === 'fixed' || style.position === 'sticky') {
                                                        el.style.display = 'none !important';
                                                        el.style.opacity = '0';
                                                        el.style.visibility = 'hidden';
                                                    }
                                                } catch(e) {}
                                            });
                                            
                                            // Injetar CSS global agressivo para forçar tudo atrás da imagem a ser branco
                                            const style = document.createElement('style');
                                            style.innerHTML = `
                                                body, html, #app, .v-application, .v-main, main, div, section { 
                                                    background-color: #FFFFFF !important; 
                                                    background-image: none !important;
                                                }
                                                .page-img, .page-img canvas, .page-img img {
                                                    background-color: transparent !important;
                                                    border: none !important;
                                                    outline: none !important;
                                                    box-shadow: none !important;
                                                    margin: 0 !important;
                                                    padding: 0 !important;
                                                    transform: none !important;
                                                }
                                            `;
                                            document.head.appendChild(style);
                                        }''')
                                        
                                        # Tenta pegar apenas o canvas primeiro (imagem exata)
                                        image_elements = page.query_selector_all('.page-img canvas')
                                        if not image_elements:
                                            image_elements = page.query_selector_all('.page-img')
                                            
                                        import base64
                                        import io
                                        for el in image_elements:
                                            try:
                                                # Scroll into view so it loads fully
                                                el.scroll_into_view_if_needed()
                                                time.sleep(0.5)
                                                
                                                # Tira o screenshot do elemento inteiro (garante que não fica quadrada caso a imagem seja muito alta)
                                                screenshot_bytes = el.screenshot(type="jpeg", quality=90)
                                                
                                                # Cortar exatamente 4 pixels da borda esquerda (conforme medida do usuário)
                                                # E garantir que as dimensões finais sejam PARES para impedir o crash do Waifu2x
                                                try:
                                                    from PIL import Image
                                                    img = Image.open(io.BytesIO(screenshot_bytes))
                                                    width, height = img.size
                                                    if width > 10 and height > 10:
                                                        left_crop = 4
                                                        new_width = width - left_crop
                                                        new_height = height
                                                        
                                                        # Ajusta a borda direita e inferior para garantir números pares
                                                        right_crop = width if new_width % 2 == 0 else width - 1
                                                        bottom_crop = height if new_height % 2 == 0 else height - 1
                                                        
                                                        # (left, upper, right, lower)
                                                        cropped_img = img.crop((left_crop, 0, right_crop, bottom_crop))
                                                        buffer = io.BytesIO()
                                                        cropped_img.save(buffer, format="JPEG", quality=90)
                                                        screenshot_bytes = buffer.getvalue()
                                                except Exception as crop_e:
                                                    logger.warning(f"Erro ao recortar a margem esquerda: {crop_e}")
                                                    
                                                b64_string = base64.b64encode(screenshot_bytes).decode('utf-8')
                                                images_data.append({'type': 'base64', 'src': f"data:image/jpeg;base64,{b64_string}"})
                                            except Exception as e:
                                                logger.warning(f"Failed to screenshot element: {e}")
                                except Exception as e:
                                    logger.warning(f"Timeout ou erro ao processar imagens da pagina: {e}")
                            
                            if headless and "/read/" in url and not images_data:
                                context.close()
                                return None
                            
                            context.close()
                            return {"html": html, "images": images_data}
                        except Exception as e:
                            logger.error(f"Failed page processing: {e}")
                            try: context.close()
                            except: pass
                            return {"html": html if 'html' in locals() else "", "images": []}
                    except Exception as e:
                        logger.error(f"Failed to launch persistent context: {e}")
                        return {"html": "", "images": []}

        # Primeiro tentamos em modo invisível
        result = run_browser(headless=True)
        if result is None:
            # Se for None, significa que precisamos fazer login (visível para o Captcha/UX)
            logger.info("Comikey: Iniciando navegador visível para autenticação...")
            result = run_browser(headless=False)
            
        return result or {"html": "", "images": []}

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos de: {series_url}")
        
        if "/read/" in series_url:
            return [series_url]

        try:
            result = self._fetch_with_playwright(series_url)
            html = result.get("html", "")
        except Exception as e:
            raise Exception(f"Falha ao obter dados da Comikey: {e}")

        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        # Na página da Comikey, os capítulos geralmente ficam listados em links de leitura
        import urllib.parse
        for a in soup.find_all('a', href=True):
            href = a['href']
            if "/read/" in href:
                full_url = urllib.parse.urljoin(series_url, href)
                links.add(full_url)
        
        def extract_num(path):
            match = re.search(r'(?:chapter|episode|ep|ch|pt|part)-?(\d+(?:\.\d+)?)', path.lower())
            if match:
                return float(match.group(1))
            parts = [p for p in path.split('/') if p]
            if parts:
                nums = re.findall(r'\d+(?:\.\d+)?', parts[-1])
                if nums: return float(nums[-1])
            return 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return sorted_links

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens do capítulo: {chapter_url}")
        
        try:
            result = self._fetch_with_playwright(chapter_url)
            images_data = result.get("images", [])
        except Exception as e:
            raise Exception(f"Falha ao extrair imagens da Comikey: {e}")

        ordered_images = []
        for img in images_data:
            ordered_images.append(img['src'])
            
        if not ordered_images:
            raise Exception("Nenhuma imagem decodificada encontrada no capítulo. O capítulo pode ser pago e a conta não o possuir, ou a proteção não foi carregada.")

        return ordered_images

    # Nota: ReadStitch suporta base64 via urllib.request se formatado como data:image/jpeg;base64,...
    # A implementação interna do downloader lida bem se as urls retornadas já forem Data URIs
