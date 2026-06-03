import re
import time
from typing import List
from playwright.sync_api import sync_playwright
from core.scrapers.base_scraper import BaseScraper

class RoliascanScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://roliascan.com"

    def get_chapters(self, series_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching series page: {series_url}")
        chapters = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            
            # Bloquear resources inúteis para agilizar o carregamento
            page.route("**/*", lambda route: route.continue_() if route.request.resource_type in ["document", "script", "xhr", "fetch"] else route.abort())
            
            try:
                page.goto(series_url, wait_until="domcontentloaded", timeout=30000)
                
                # Clica na aba "Chapters" se existir (muito comum em sites MangaTaro)
                try:
                    page.wait_for_selector('text="Chapters"', timeout=5000)
                    page.evaluate("""() => {
                        let tabs = Array.from(document.querySelectorAll('button, a, div')).filter(el => el.textContent.trim().toLowerCase() === 'chapters' || el.textContent.trim().toLowerCase() === 'capítulos');
                        if (tabs.length > 0) {
                            tabs[0].click();
                        }
                    }""")
                    time.sleep(1)
                except Exception as e:
                    pass
                
                # Aguarda até que pelo menos um link de capítulo apareça
                # Roliascan links geralmente tem '/read/' e '/ch'
                try:
                    page.wait_for_selector('a[href*="/read/"]', timeout=10000)
                except:
                    pass
                
                # Rolar até o fim da página para garantir que todos os capítulos carreguem (se tiver scroll infinito)
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(0.5)
                
                links = page.locator('a[href*="/read/"]').all()
                if not links:
                    links = page.locator('a[href*="/chapter"]').all()
                
                seen = set()
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            href = self.base_url + href
                        if href not in seen:
                            seen.add(href)
                            chapters.append(href)
                
                # Opcional: ordenar corretamente. A maioria das fontes lista do mais novo ao mais velho, 
                # e o BaseScraper costuma reverter se necessário. Mas garantiremos apenas os únicos.
                print(f"[{self.__class__.__name__}] Found {len(chapters)} chapters.")
                
            except Exception as e:
                print(f"[{self.__class__.__name__}] Error fetching chapters: {e}")
            finally:
                browser.close()
                
        return chapters

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        print(f"[{self.__class__.__name__}] Fetching images for chapter: {chapter_url}")
        images = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            
            # Não bloquear imagens aqui, pois precisamos que os data-src carreguem, 
            # mas podemos bloquear fontes e media.
            page.route("**/*", lambda route: route.continue_() if route.request.resource_type not in ["media", "font"] else route.abort())
            
            try:
                page.goto(chapter_url, wait_until="domcontentloaded", timeout=30000)
                
                # Aguarda as imagens do container aparecerem
                try:
                    page.wait_for_selector('img', timeout=10000)
                except:
                    pass
                
                # Rola para forçar lazy load e coleta as imagens DURANTE o scroll
                # Isso é crucial porque sites com 'Virtual Scrolling' removem as imagens antigas do DOM.
                last_height = 0
                for _ in range(50): # Aumentado para capítulos maiores
                    # Coleta as imagens visíveis no momento
                    imgs = page.locator('img').all()
                    for img in imgs:
                        try:
                            data_src = img.get_attribute('data-src')
                            real_src = data_src if data_src else img.get_attribute('src')
                            
                            if real_src and not real_src.startswith('data:image'):
                                lower_src = real_src.lower()
                                if 'avatar' not in lower_src and 'logo' not in lower_src and 'icon' not in lower_src and 'adskeeper' not in lower_src and 'pubadx' not in lower_src and 'makima.webp' not in lower_src and '-cover-' not in lower_src:
                                    if real_src.startswith('/'):
                                        real_src = self.base_url + real_src
                                    elif real_src.startswith('//'):
                                        real_src = 'https:' + real_src
                                    
                                    if real_src not in images:
                                        images.append(real_src)
                        except Exception:
                            # Ignora erros se o elemento for removido do DOM durante a leitura
                            pass
                            
                    # Rola a página
                    page.evaluate("window.scrollBy(0, 1500)")
                    time.sleep(0.4)
                    
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        # Tenta dar um scrollzinho a mais pra garantir que não travou
                        page.evaluate("window.scrollBy(0, 500)")
                        time.sleep(0.5)
                        if page.evaluate("document.body.scrollHeight") == last_height:
                            break
                    last_height = new_height
                                
                print(f"[{self.__class__.__name__}] Found {len(images)} images.")
                
            except Exception as e:
                print(f"[{self.__class__.__name__}] Error fetching images: {e}")
            finally:
                browser.close()
                
        return images
