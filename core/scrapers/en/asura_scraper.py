import urllib.request
import re
from ..base_scraper import BaseScraper

class AsuraScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://asurascans.com"
        self.credentials = None
        self._logged_in = False

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')

    def _fetch_chapter_with_playwright(self, chapter_url, email, password):
        print(f"[AsuraScraper] Iniciando Playwright para o capítulo: {chapter_url}")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                # Janela pequena para não incomodar muito
                page = browser.new_page(viewport={'width': 800, 'height': 600})
                
                # 1. Ir direto para o capítulo
                page.goto(chapter_url, wait_until="networkidle")
                
                # 2. Tentar preencher o login que aparece no próprio capítulo
                try:
                    # Se não aparecer em 10 segundos, talvez já esteja logado ou não seja esse o bloqueio
                    page.wait_for_selector('input[type="email"]', timeout=10000)
                    print("[AsuraScraper] Formulário de login encontrado no capítulo. Autenticando...")
                    page.fill('input[type="email"]', email)
                    page.fill('input[type="password"]', password)
                    page.click('button[type="submit"]')
                    
                    # Esperar o reload ou o carregamento das imagens após logar
                    page.wait_for_timeout(5000)
                except Exception as e:
                    print("[AsuraScraper] Não achou formulário ou timeout. Buscando imagens direto...")
                
                # 3. Extrair as imagens direto do DOM carregado
                print("[AsuraScraper] Extraindo imagens renderizadas...")
                imgs = page.locator("img").all()
                
                seen = set()
                ordered = []
                for img in imgs:
                    src = img.get_attribute("src")
                    if src and "/asura-images/chapters/" in src:
                        if src not in seen:
                            seen.add(src)
                            ordered.append(src)
                
                browser.close()
                return ordered
        except Exception as e:
            print(f"[AsuraScraper] Erro no fluxo do Playwright: {e}")
            return []

    def get_chapters(self, series_url):
        """
        Fetches the series page and extracts a list of all chapter URLs.
        Returns a sorted list of absolute chapter URLs.
        If a chapter URL is provided, returns just that chapter.
        """
        if "/chapter/" in series_url:
            return [series_url]
            
        try:
            html = self._fetch_html(series_url)
        except Exception as e:
            raise Exception(f"Failed to fetch series page: {e}")

        # Extract slug from URL
        slug = [p for p in series_url.split('/') if p][-1]
        
        # Regex to find /comics/slug/chapter/X
        pattern = r'href=[\'\"](/comics/' + re.escape(slug) + r'/chapter/[^\'\"]+)[\'\"]'
        links = set(re.findall(pattern, html))
        
        def extract_num(path):
            match = re.search(r'chapter(?:-|\/)(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return [self.base_url + l for l in sorted_links]

    def _extract_images_from_html(self, html):
        # Asura stores JSON props in HTML where quotes are HTML-escaped.
        html = html.replace('&quot;', '"')
        images = re.findall(r'https://cdn\.asurascans\.com/asura-images/chapters/[^\"\']+\.(?:webp|jpg|png)', html)
        if not images:
            # Maybe the domain is different now (e.g. asuracomic)
            images = re.findall(r'https://.*?/asura-images/chapters/[^\"\']+\.(?:webp|jpg|png)', html)
            
        seen = set()
        ordered = []
        for img in images:
            if img not in seen:
                seen.add(img)
                ordered.append(img)
        return ordered

    def get_chapter_images(self, chapter_url):
        """
        Fetches the chapter page and extracts all image URLs.
        """
        try:
            html = self._fetch_html(chapter_url)
        except Exception as e:
            raise Exception(f"Failed to fetch chapter page: {e}")
            
        images = self._extract_images_from_html(html)
        
        # Se não vieram imagens e temos credenciais configuradas, usar Playwright para logar e ler o capítulo
        if not images and self.credentials:
            print("[AsuraScraper] Nenhuma imagem encontrada. Capítulo pode ser pago. Ativando Playwright...")
            email, password = self.credentials
            images = self._fetch_chapter_with_playwright(chapter_url, email, password)
                
        return images
