import logging
import urllib.request
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PlumaComicsScraper(BaseScraper):
    """Scraper para o site Pluma Comics."""
    
    @property
    def name(self):
        return "Pluma Comics"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        chapters = []
        # O Tachiyomi seleciona links dentro de .card que contenham ler
        for a in soup.select('a[href*="/ler/"]'):
            href = a.get('href')
            if not href:
                continue
                
            # Extrair o nome do capítulo
            # O texto geralmente está num span dentro do 'a' ou é o próprio texto do link
            span = a.find('span')
            title = span.get_text(strip=True) if span else a.get_text(strip=True)
            
            title_lower = title.lower()
            if "começar" in title_lower or "último" in title_lower or "leitura" in title_lower:
                continue
            
            # Monta a URL absoluta com o título como âncora para a GUI usar no nome do capítulo
            url = urljoin("https://plumacomics.cloud", href)
            # Adiciona o título como âncora, ex: url#capitulo-1
            if title:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', title)
                if match:
                    url = f"{url}#capitulo-{match.group(1)}"
                else:
                    title_clean = title.replace(' ', '-').replace('\n', '')
                    url = f"{url}#{title_clean}"
                
            chapters.append(url)
            
        # Deduplicar preservando a ordem (que costuma ser do mais recente para o mais antigo)
        seen = set()
        ordered_chapters = []
        for ch in chapters:
            if ch not in seen:
                seen.add(ch)
                ordered_chapters.append(ch)
                
        if not ordered_chapters:
            logger.error(f"[{self.name}] Nenhum capítulo encontrado")
            raise Exception("Não foi possível encontrar a lista de capítulos")
            
        logger.info(f"[{self.name}] Encontrados {len(ordered_chapters)} capítulos")
        return ordered_chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        # O ID do capítulo é a última parte da URL ignorando a âncora
        # ex: https://plumacomics.cloud/ler/2463#Capitulo-1
        clean_url = chapter_url.split('#')[0].strip('/')
        chapter_id = clean_url.split('/')[-1]
        api_url = f"https://plumacomics.cloud/api/viewer/bootstrap?c={chapter_id}"
        
        try:
            req = urllib.request.Request(api_url, headers=self.headers)
            resp = urllib.request.urlopen(req).read().decode('utf-8')
            data = json.loads(resp)
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao consultar API de leitura: {e}")
            raise Exception("Falha ao obter dados do capítulo via API")
            
        if 'pages' not in data:
            logger.error(f"[{self.name}] Nenhuma imagem no JSON retornado")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        images = []
        for page in data['pages']:
            u = page.get('u')
            if u:
                img_url = urljoin("https://plumacomics.cloud", u)
                images.append(img_url)
                
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
