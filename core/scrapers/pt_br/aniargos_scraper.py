import logging
import json
import re
from ..base_scraper import BaseScraper
from core.cloudflare_bypass import get_cookie_header

logger = logging.getLogger(__name__)

class AniArgosScraper(BaseScraper):
    """
    Scraper para o site AniArgos.
    Requer login via Playwright para obter o access_token,
    depois usa urllib para extrair capítulos e imagens da estrutura SSR (Next.js).
    """
    
    @property
    def name(self):
        return "AniArgos"

    def __init__(self):
        super().__init__()
        self.base_url = "https://aniargos.com"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': f"{self.base_url}/"
        })
        self._load_cookies()

    def _load_cookies(self):
        cookie_header = get_cookie_header("aniargos.com")
        if cookie_header:
            self.headers['Cookie'] = cookie_header

    def login(self, email, password):
        logger.info(f"[{self.name}] Tentando fazer login via Playwright...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"{self.base_url}/login")
                
                # Preenche as credenciais e loga
                page.fill('input[type="email"]', email)
                page.fill('input[type="password"]', password)
                page.click('button[type="submit"]')
                
                # Aguarda o redirecionamento ou o cookie access_token ser setado
                page.wait_for_timeout(4000)
                
                cookies = page.context.cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                
                if "access_token" in cookie_str:
                    logger.info(f"[{self.name}] Login bem-sucedido! Access token obtido.")
                    self.headers['Cookie'] = cookie_str
                    # Opcional: salvar os cookies globais se o gerenciador suportar salvar com domínio específico
                    # Aqui apenas mantemos na instância para uso atual.
                else:
                    raise Exception("Falha no login: Cookie access_token não encontrado após o login.")
                    
                browser.close()
        except Exception as e:
            logger.error(f"[{self.name}] Erro no login automatizado: {e}")
            raise Exception(f"Erro ao fazer login no AniArgos: {e}")

    def _get_page_content_with_playwright(self, url: str, return_images=False):
        from playwright.sync_api import sync_playwright
        intercepted_images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            if 'Cookie' in self.headers:
                cookies = []
                for c in self.headers['Cookie'].split(';'):
                    if '=' in c:
                        k, v = c.strip().split('=', 1)
                        cookies.append({
                            'name': k,
                            'value': v,
                            'domain': 'aniargos.com',
                            'path': '/'
                        })
                context.add_cookies(cookies)
            
            page = context.new_page()
            
            if return_images:
                def handle_request(request):
                    req_url = request.url
                    if ('supabase' in req_url or 'cdn.aniargos' in req_url) and 'logo' not in req_url.lower():
                        if req_url not in intercepted_images:
                            intercepted_images.append(req_url)
                page.on("request", handle_request)
                
            page.goto(url, wait_until="networkidle")
            
            if return_images:
                # Scroll robusto universal para lazy-load infinito (inclui containers de layout)
                try:
                    scroll_script = """
                    (async () => {
                        const getAllScrollables = () => {
                            const scrollables = [window];
                            const all = document.querySelectorAll('*');
                            for (let el of all) {
                                const style = window.getComputedStyle(el);
                                if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                                    scrollables.push(el);
                                }
                            }
                            return scrollables;
                        };
                        
                        let noChangeCount = 0;
                        while(noChangeCount < 5) {
                            let changed = false;
                            const scrollables = getAllScrollables();
                            for (let el of scrollables) {
                                let prev;
                                if (el === window) {
                                    prev = window.scrollY;
                                    window.scrollBy(0, 800);
                                    if (window.scrollY > prev) changed = true;
                                } else {
                                    prev = el.scrollTop;
                                    el.scrollBy(0, 800);
                                    if (el.scrollTop > prev) changed = true;
                                }
                            }
                            if (changed) {
                                noChangeCount = 0;
                            } else {
                                noChangeCount++;
                            }
                            await new Promise(r => setTimeout(r, 200));
                        }
                    })()
                    """
                    page.evaluate(scroll_script)
                    page.wait_for_timeout(1000)
                except:
                    pass
            else:
                page.wait_for_timeout(1000) # Espera carregar o React
            
            # Tenta clicar na aba "Capítulos" se existir, para forçar renderização
            try:
                page.evaluate("() => { const tabs = Array.from(document.querySelectorAll('button, a, div.cursor-pointer, li')).filter(el => el.textContent.includes('Capítulos')); if(tabs.length) tabs[0].click(); }")
                page.wait_for_timeout(2000)
            except:
                pass
                
            html = page.content()
            browser.close()
            if return_images:
                return html, intercepted_images
            return html

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        if 'Cookie' not in self.headers or 'access_token' not in self.headers['Cookie']:
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("aniargos_email")
                password = settings.load("aniargos_password")
                
                if not email or not password:
                    raise Exception("Necessário preencher o login e senha no Baixador para o site AniArgos.")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")
            
        try:
            html = self._get_page_content_with_playwright(series_url)
            
            # Busca as rotas de capítulos em qualquer lugar do HTML (inclusive payloads JSON do NextJS)
            chapters_paths = re.findall(r'(/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+/capitulo/[0-9.]+)', html)
            if not chapters_paths:
                chapters_paths = re.findall(r'href=["\'](/[^"\'/]+/[^"\'/]+/capitulo/[0-9.]+)["\']', html)
            if not chapters_paths:
                chapters_paths = re.findall(r'(/work/[a-zA-Z0-9_\-]+/capitulo/[0-9.]+)', html)
            if not chapters_paths:
                chapters_paths = re.findall(r'href=["\'](/[^"\']+capitulo/[0-9.]+)["\']', html)
            
            if not chapters_paths:
                # Procura no estado do next_f
                chapters_paths = re.findall(r'\\"href\\":\\"(/[^"\']+capitulo/[0-9.]+)\\"', html)
            
            if not chapters_paths:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    if 'capitulo' in a['href']:
                        chapters_paths.append(a['href'])
                        
            if not chapters_paths:
                # Tenta match em URLs brutos Next.js (slug/capitulo/num)
                m = re.findall(r'/[^"\'\\]+/[^"\'\\]+/capitulo/[0-9.]+', html)
                chapters_paths.extend(m)
                
            # Filtra apenas os links que pertencem à obra (evita pegar de "recomendados" no sidebar)
            import urllib.parse
            parsed_url = urllib.parse.urlparse(series_url)
            slug = parsed_url.path.strip('/').split('/')[-1]
            if slug:
                chapters_paths = [p for p in chapters_paths if slug in p]
                
            chapters_paths = list(set(chapters_paths))
            
            def get_num(path):
                try:
                    return float(path.split('/')[-1])
                except:
                    return 0
                    
            chapters_paths = sorted(chapters_paths, key=get_num, reverse=True)
            all_chapters = [f"{self.base_url}{path}" if path.startswith('/') else path for path in chapters_paths]
            
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capítulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capítulos: {e}")
            raise Exception(f"Falha ao obter a lista de capítulos: {e}")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        if 'Cookie' not in self.headers or 'access_token' not in self.headers['Cookie']:
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("aniargos_email")
                password = settings.load("aniargos_password")
                
                if not email or not password:
                    raise Exception("Necessário preencher o login e senha no Baixador para o site AniArgos.")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")
                
        try:
            html, intercepted_images = self._get_page_content_with_playwright(chapter_url, return_images=True)
            
            images = intercepted_images
            
            # Tenta pegar das imagens renderizadas no DOM se a interceptação falhou
            if not images:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('srcset')
                    if src and ('supabase' in src or 'cdn' in src or '_next/image' in src) and 'logo' not in src.lower():
                        if src.startswith('/_next/image?url='):
                            import urllib.parse
                            actual_src = urllib.parse.unquote(src.split('url=')[1].split('&')[0])
                            images.append(actual_src)
                        else:
                            images.append(src if src.startswith('http') else f"https:{src}" if src.startswith('//') else f"{self.base_url}{src}")
                            
            if not images:
                # Tenta regex no NextJS Data
                m = re.search(r'\\"pages\\":(\[.*?\])', html)
                if m:
                    pages_str = m.group(1).replace('\\"', '"')
                    images_list = json.loads(pages_str)
                    for img in images_list:
                        if img.startswith('http'):
                            images.append(img)
                        elif img.startswith('//'):
                            images.append(f"https:{img}")
                        else:
                            images.append(f"https://cdn.aniargos.com{img}")
                            
            # Remover duplicatas mantendo ordem
            seen = set()
            unique_images = []
            for img in images:
                # Filtrar _next/image final URL
                if '/_next/image?url=' in img:
                    import urllib.parse
                    img = urllib.parse.unquote(img.split('url=')[1].split('&')[0])
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            images = unique_images
            
            if not images:
                raise Exception("Não foi possível encontrar as imagens na página do capítulo. Talvez bloqueado por paywall/moedas?")
                
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar o capítulo: {e}")
            raise Exception("Falha ao obter imagens do capítulo")
