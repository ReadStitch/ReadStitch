import json
import logging
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class DropeScanScraper(BaseScraper):
    """Scraper para o site Drope Scan."""
    
    @property
    def name(self):
        return "Drope Scan"

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        req = urllib.request.Request(series_url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        
        chapters = []
        if script:
            try:
                data = json.loads(script.string)
                series_data = data.get('props', {}).get('pageProps', {}).get('data', {})
                chapters_data = series_data.get('Chapters', [])
                
                # Sort chapters by ChapterNumber descending
                def parse_chapter_num(c):
                    try:
                        return float(c.get('ChapterNumber', 0))
                    except (ValueError, TypeError):
                        return 0.0
                
                chapters_data = sorted(chapters_data, key=parse_chapter_num, reverse=True)
                
                # Extract URLs
                for chapter in chapters_data:
                    c_id = chapter.get('ChapterId')
                    c_version = chapter.get('ChapterVersion', '1')
                    obra_id = chapter.get('ChapterObraId')
                    chapter_number = chapter.get('ChapterNumber')
                    
                    if not obra_id:
                        # Se não tiver, tenta extrair da URL da série
                        parsed = urlparse(series_url)
                        parts = parsed.path.strip('/').split('/')
                        if len(parts) >= 2 and parts[0] == 'obras':
                            obra_id = parts[1]
                    
                    if c_id and obra_id:
                        url = f"https://beta.dropescan.com/obras/{obra_id}/{c_id}/{c_version}"
                        if chapter_number is not None:
                            url += f"?chapter={chapter_number}"
                        chapters.append(url)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao parsear JSON das chapters: {e}")
        
        # Fallback para parsing de HTML caso o JSON não funcione ou mude
        if not chapters:
            parsed = urlparse(series_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            links = soup.find_all('a', href=True)
            seen_urls = set()
            import re
            for a in links:
                href = a['href']
                if '/obras/' in href and href.count('/') >= 4: # /obras/id/cap_id/1
                    full_url = f"{base_url}{href}" if href.startswith('/') else href
                    base_full = full_url.split('?')[0]
                    if base_full not in seen_urls and base_full != series_url.split('?')[0]:
                        seen_urls.add(base_full)
                        chapter_text = a.get_text(strip=True)
                        match = re.search(r'(?:Capítulo|Cap|Chapter|Ch)\s*(\d+(?:\.\d+)?)', chapter_text, re.IGNORECASE)
                        if match:
                            full_url += f"?chapter={match.group(1)}"
                        chapters.append(full_url)
                        
        def get_chapter_num(link):
            # Tenta pegar algo do tipo /1, mas o último número é a versão.
            # Melhor tentar procurar a palavra Capítulo ou o número antes
            # Aqui como fallback para link sem info, extrairemos do HTML original se possível, mas só temos URL
            pass # A lista JSON já pode vir ordenada, ou podemos manter a ordem original
            
        # Manteremos a ordem do JSON que costuma ser descrescente, ou se usarmos HTML pode vir descrescente tbm.
        # Mas para garantir, podemos não reordenar e deixar a lista como vem.
        
        return chapters

    def get_chapter_images(self, chapter_url):
        clean_url = chapter_url.split('?')[0].split('#')[0]
        logger.info(f"[{self.name}] Fetching images from: {clean_url}")
        
        req = urllib.request.Request(clean_url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        
        images = []
        if script:
            try:
                data = json.loads(script.string)
                pages = data.get('props', {}).get('pageProps', {}).get('pages', [])
                
                # Order pages by pageNumber
                def page_num(p):
                    try:
                        return int(p.get('pageNumber', 0))
                    except (ValueError, TypeError):
                        return 0
                
                pages = sorted(pages, key=page_num)
                
                for p in pages:
                    src = p.get('source')
                    if src:
                        if src.startswith('http'):
                            images.append(src)
                        else:
                            images.append(f"https://bucket-1.dropescan.com/{src}")
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao parsear JSON das imagens: {e}")
                
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis ou a página está protegida.")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
