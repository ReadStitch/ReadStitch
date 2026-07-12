import re
import logging
from typing import List

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ImperioDaBritanniaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://imperiodabritannia.net"

    @property
    def name(self):
        return "Império da Britannia"

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
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
            
            while scroll_attempts < 30:  # Limite máximo de cliques
                try:
                    chaps = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('capitulo') || h.includes('chapter'))")
                    chapters.update(chaps)
                    
                    # Rolar um pouco para baixo
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(500)
                    
                    # Tentar clicar no botão "Ver Mais (X)"
                    clicked = page.evaluate('''() => {
                        let btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Ver Mais') || b.innerText.includes('Carregar'));
                        let visibleBtn = btns.find(b => b.offsetParent !== null);
                        if (visibleBtn) {
                            visibleBtn.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    if clicked:
                        page.wait_for_timeout(1500)
                        scroll_attempts += 1
                    else:
                        # Se não achar o botão, extrai os links pela última vez e sai
                        chaps = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('capitulo') || h.includes('chapter'))")
                        chapters.update(chaps)
                        break
                except Exception as e:
                    logger.warning(f"[{self.name}] Erro no scroll/clique do Playwright: {e}")
                    break
                    
            browser.close()

        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado em {series_url}")

        sorted_chapters = []
        for url in chapters:
            match = re.search(r'(?:capitulo|chapter)(?:[-_/\s]*)?([\d.]+)', url, re.IGNORECASE)
            if match:
                num = float(match.group(1))
                sorted_chapters.append((num, url))
            else:
                sorted_chapters.append((0.0, url))
                
        sorted_chapters.sort(key=lambda x: x[0])
        return [c[1] for c in sorted_chapters]

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Buscando imagens do capítulo em: {chapter_url}")
        
        from playwright.sync_api import sync_playwright
        
        images = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(chapter_url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                logger.warning(f"[{self.name}] Erro ao acessar o capítulo, tentando prosseguir: {e}")
                
            # Scroll até o final da página para garantir o carregamento das imagens em lazy-load
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            
            imgs = page.evaluate("Array.from(document.querySelectorAll('img')).map(i => i.src)")
            
            for src in imgs:
                # Filtrar imagens reais do capítulo e ignorar banners, logos etc.
                if 'cdn.imperiodabritannia.net' in src or 'obras' in src or 'chapter' in src or 'capitulo' in src:
                    if not any(ignore in src.lower() for ignore in ['logo', 'avatar', 'icon', 'profile', 'svg', 'banner', 'ads']):
                        if src not in images:
                            images.append(src)

            browser.close()

        if not images:
            raise Exception("O capítulo não possui imagens acessíveis.")
            
        return images
