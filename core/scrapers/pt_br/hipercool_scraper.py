import logging
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class HipercoolScraper(BaseScraper):
    """Scraper para o site LerHentais (antigo Hipercool/Hipertoon)."""
    
    @property
    def name(self):
        return "LerHentais (Hipercool)"

    def __init__(self):
        super().__init__()
        self.headers.update({
            'Referer': 'https://lerhentais.com/'
        })

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        # Garante o domínio correto
        series_url = series_url.replace("hipertoon.com", "lerhentais.com").replace("hiper.cool", "lerhentais.com").rstrip('/')
        
        from playwright.sync_api import sync_playwright
        
        chapters = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            def handle_response(response):
                if "series.chapters" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        for item in data:
                            json_data = item.get('result', {}).get('data', {}).get('json')
                            if isinstance(json_data, list) and len(json_data) > 0 and 'seriesId' in json_data[0]:
                                for c in json_data:
                                    chapters.append(c)
                    except Exception:
                        pass
                        
            page.on("response", handle_response)
            
            try:
                page.goto(series_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao carregar página da série: {e}")
                
            browser.close()
            
        if not chapters:
            raise Exception("Não foi possível interceptar a lista de capítulos via API")
            
        chapter_urls = []
        for chap in chapters:
            number = chap.get('number')
            if number is not None:
                # O formato do LerHentais é /manga/slug/numero
                chap_url = f"{series_url}/{number}"
                chapter_urls.append(chap_url)
                
        logger.info(f"[{self.name}] Encontrados {len(chapter_urls)} capítulos")
        return chapter_urls

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        chapter_url = chapter_url.replace("hipertoon.com", "lerhentais.com").replace("hiper.cool", "lerhentais.com")
        
        from playwright.sync_api import sync_playwright
        
        images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            intercepted_images = []
            def handle_request(request):
                if request.resource_type in ["image", "fetch"]:
                    src = request.url.lower()
                    if ('capitulo' in src or 'upload' in src or 'media' in src or 'manga' in src) and 'logo' not in src and 'avatar' not in src:
                        # ignorar urls muito pequenas ou não relacionadas a paginas
                        if request.url not in intercepted_images:
                            intercepted_images.append(request.url)
            page.on("request", handle_request)
            
            try:
                page.goto(chapter_url, wait_until="networkidle", timeout=30000)
                
                # Scroll robusto universal para lazy-load
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
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao carregar página do capítulo: {e}")
                
            images = intercepted_images
            
            if not images:
                # Fallback para o DOM
                img_elements = page.query_selector_all("img")
                for img in img_elements:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and ('capitulo' in src.lower() or 'upload' in src.lower() or 'media' in src.lower() or 'manga' in src.lower()):
                        if src.startswith('http'):
                            if src not in images:
                                images.append(src)
                                
            browser.close()
            
        if not images:
            logger.error(f"[{self.name}] Nenhuma imagem extraída do DOM")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
