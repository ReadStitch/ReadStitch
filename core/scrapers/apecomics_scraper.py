import logging
import urllib.request
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ApeComicsScraper(BaseScraper):
    """Scraper para o site ApeComics (atual Capitoons)."""
    
    @property
    def name(self):
        return "ApeComics (Capitoons)"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        html = self._fetch_html(series_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # O site capitoons usa um div com id "chapter_list" e os links estão lá dentro
        chapter_list_container = soup.find('div', id='chapter_list')
        
        if not chapter_list_container:
            logger.error(f"[{self.name}] Container de capítulos não encontrado")
            raise Exception("Não foi possível encontrar a lista de capítulos")

        chapters = []
        # Encontra todos os links de capítulos
        items = chapter_list_container.find_all('a')
        
        for item in items:
            href = item.get('href')
            if not href:
                continue
                
            # O título do capítulo está dentro de um span com class "line-clamp-1"
            title_span = item.find('span', class_='line-clamp-1')
            if title_span:
                title = title_span.text.strip()
            else:
                # Fallback: tentar pegar do texto ou url
                title = item.text.strip() or href.split('/')[-2].replace('-', ' ').title()
                
            # Evita adicionar links vazios ou duplicados anormais
            chapters.append(href)
            
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        html = self._fetch_html(chapter_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # As imagens estão dentro de div.reader-area > img
        reader_area = soup.find('div', class_='reader-area')
        
        if not reader_area:
            logger.error(f"[{self.name}] Área de leitura não encontrada")
            raise Exception("Não foi possível encontrar as imagens do capítulo")
            
        images = []
        for img in reader_area.find_all('img'):
            # Algumas vezes eles podem usar 'data-src' ou 'src' para lazy loading
            src = img.get('data-src') or img.get('src')
            if src:
                src = src.strip()
                images.append(src)
                
        if not images:
            logger.error(f"[{self.name}] Nenhuma imagem extraída")
            raise Exception("O capítulo não possui imagens acessíveis")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
        return images
