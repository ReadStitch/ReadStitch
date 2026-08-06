from playwright.sync_api import sync_playwright
from ..base_scraper import BaseScraper
import time

class KakaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    def get_chapter_groups(self, series_url, progress_callback=None):
        return {"Padrão": self.get_chapters(series_url, progress_callback=progress_callback)}
        
    def get_chapters(self, series_url, progress_callback=None):
        if not series_url.startswith('http'):
            series_url = 'https://' + series_url
            
        if "viewer=" in series_url or "/viewer/" in series_url:
            return [series_url]
            
        chapters = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            
            if progress_callback: progress_callback("Iniciando navegador invisível para o KakaoPage...")
            try:
                page.goto(series_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3) # Wait for SPA to render
            except:
                pass
                
            max_clicks = 60
            clicks = 0
            empty_reads = 0
            
            while clicks < max_clicks:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                
                # Fetch currently loaded chapters to show progress
                if progress_callback:
                    curr_chaps = page.evaluate("document.querySelectorAll('li.list-child-item').length")
                    progress_callback(f"Rolando a página... {curr_chaps} capítulos encontrados (Clique {clicks}/{max_clicks})")
                
                btn = page.query_selector("img[alt='아래 화살표']")
                if btn:
                    empty_reads = 0
                    try:
                        parent = btn.evaluate_handle("el => el.parentElement")
                        if parent:
                            parent.click()
                            time.sleep(0.5)
                            clicks += 1
                            continue
                    except:
                        pass
                else:
                    empty_reads += 1
                    if empty_reads >= 5:
                        break # Give up if no button found after 5 scroll attempts
                    time.sleep(1)
                    continue
                    
                break
                
            if progress_callback: progress_callback("Extraindo links dos capítulos carregados...")
                
            links = page.evaluate("""() => {
                let items = document.querySelectorAll("li.list-child-item");
                return Array.from(items).map(li => {
                    let text = li.innerText.replace(/\\n/g, ' ');
                    let a = li.querySelector("a[href*='/viewer/']");
                    let url = a ? a.href : '';
                    return {text: text, url: url};
                }).filter(x => x.url !== '');
            }""")
            
            import re
            for item in links:
                url = item['url']
                text = item['text']
                # Tentar extrair o número do capítulo do texto da tela (ex: "001화")
                num_match = re.search(r'(\d+(?:\.\d+)?)\s*화', text)
                if not num_match:
                    num_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    
                if num_match:
                    # Inserir chapter= para a regex da interface capturar e nomear bonito
                    if '?' in url:
                        url = f"{url}&chapter={num_match.group(1)}"
                    else:
                        url = f"{url}?chapter={num_match.group(1)}"
                
                # Check for duplicates based on original viewer url (ignore the appended query parameter)
                base_url = url.split('?chapter=')[0].split('&chapter=')[0]
                if not any(base_url in existing_url for existing_url in chapters):
                    chapters.append(url)
                    
            browser.close()
            
        if not chapters:
            raise Exception("Não foi possível carregar a lista de capítulos. Verifique se a URL está correta ou forneça o link direto do visualizador.")
            
        chapters.reverse()
        return chapters

    def get_chapter_images(self, chapter_url):
        images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            
            try:
                page.goto(chapter_url, wait_until="domcontentloaded", timeout=20000)
            except:
                pass
                
            # Dar tempo para o visualizador montar a estrutura básica do React
            time.sleep(2)
            
            page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        let distance = 600;
                        let timer = setInterval(() => {
                            let scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if(totalHeight >= scrollHeight + window.innerHeight){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """)
            
            # Dar tempo para as últimas imagens baixarem
            time.sleep(2)
            
            imgs = page.evaluate("""() => Array.from(document.querySelectorAll('img')).map(i => i.src)""")
            
            for img in imgs:
                if ('download' in img or 'kakaocdn' in img) and 'svg' not in img and 'resize' not in img and 'th3' not in img:
                    if img not in images:
                        images.append(img)
                    
            browser.close()
            
        return images
