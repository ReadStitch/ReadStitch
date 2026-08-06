import urllib.request
import re
import logging
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class AcervoEremitaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://acervoeremita.com"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/"
        })

    @property
    def name(self):
        return "Acervo Eremita"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        # O Acervo Eremita utiliza Next.js com React Server Components e virtualização da lista de capítulos.
        # Para coletar todos os capítulos, usaremos o Playwright para fazer scroll no final da lista
        # diversas vezes até que não surjam mais novos capítulos.
        
        from playwright.sync_api import sync_playwright
        
        chapters = set()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(series_url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                logger.warning(f"[{self.name}] Erro ao carregar página, continuando mesmo assim: {e}")
                
            last_len = 0
            scroll_attempts = 0
            
            # Script que rola a lista até o fim
            scroll_script = '''() => {
                const links = Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('read?chapter='));
                if (links.length > 0) {
                    const lastLink = links[links.length - 1];
                    lastLink.scrollIntoView({behavior: "smooth", block: "end"});
                    
                    let parent = lastLink.parentElement;
                    while (parent && parent !== document.body) {
                        if (parent.scrollHeight > parent.clientHeight) {
                            parent.scrollBy(0, 1000);
                        }
                        parent = parent.parentElement;
                    }
                }
            }'''
            
            while scroll_attempts < 100:  # Limite máximo de iterações
                try:
                    chaps = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('read?chapter='))")
                    chapters.update(chaps)
                    
                    if len(chapters) == last_len:
                        page.wait_for_timeout(1500)
                        chaps = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('read?chapter='))")
                        chapters.update(chaps)
                        if len(chapters) == last_len:
                            break # Fim da lista
                            
                    last_len = len(chapters)
                    scroll_attempts += 1
                    
                    page.evaluate(scroll_script)
                    page.wait_for_timeout(300)
                except Exception as e:
                    logger.warning(f"[{self.name}] Erro no scroll do Playwright: {e}")
                    break
                    
            browser.close()

        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")

        # Ordenar os capítulos de forma inteligente (o URL possui o número do capítulo, ex: chapter=1.00)
        sorted_chapters = []
        for url in chapters:
            match = re.search(r'chapter=([\d.]+)', url)
            if match:
                num = float(match.group(1))
                sorted_chapters.append((num, url))
            else:
                sorted_chapters.append((0.0, url))
                
        # Retorna a lista de URLs ordenadas pelo número (crescente) e remove as duplicatas da tupla
        sorted_chapters.sort(key=lambda x: x[0])
        return [c[1] for c in sorted_chapters]

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens do capítulo em: {chapter_url}")
        
        # As imagens do Acervo Eremita não usam criptografia, são servidas diretamente no HTML da página do capítulo (nas tags <img>).
        html = self._fetch_html(chapter_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        images = []
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and '/pagesv/' in src:
                full_src = f"{self.base_url}{src}" if src.startswith('/') else src
                if full_src not in images:
                    images.append(full_src)
                    
        # Se não achou com '/pagesv/', procura qualquer imagem que pareça ser uma página de mangá
        if not images:
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and ('work' in src or 'chapter' in src or src.endswith(('.jpg', '.png', '.webp'))):
                    # Ignorar avatars, logos, icons, etc
                    if not any(ignore in src.lower() for ignore in ['logo', 'avatar', 'icon', 'profile', 'svg']):
                        full_src = f"{self.base_url}{src}" if src.startswith('/') else src
                        if full_src not in images:
                            images.append(full_src)

        if not images:
            raise Exception("O capítulo não possui imagens acessíveis.")
            
        return images
