import logging
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PlumaComicsScraper(BaseScraper):
    """Scraper para o site Pluma Comics."""
    
    def __init__(self):
        super().__init__()
        self.headers['Referer'] = 'https://plumacomics.cloud/'
        self.headers['Origin'] = 'https://plumacomics.cloud'

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
        
        if "Breve Manutenção" in html or "em manutenção" in html.lower():
            logger.error(f"[{self.name}] Site em manutenção")
            raise Exception("O site Pluma Comics está em manutenção no momento.")
            
        soup = BeautifulSoup(html, 'html.parser')
        
        chapters = []
        # O Tachiyomi seleciona links dentro de .card que contenham ler ou agora /view/
        for a in soup.select('a[href*="/view/"]'):
            href = a.get('href')
            if not href:
                continue
                
            # Extrair o nome do capítulo
            span = a.find('span')
            title = span.get_text(strip=True) if span else a.get_text(strip=True)
            
            title_lower = title.lower()
            if "começar" in title_lower or "último" in title_lower or "leitura" in title_lower:
                continue
            
            # Monta a URL absoluta com o título como âncora para a GUI usar no nome do capítulo
            url = urljoin("https://plumacomics.cloud", href)
            if title:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', title)
                if match:
                    url = f"{url}#capitulo-{match.group(1)}"
                else:
                    title_clean = title.replace(' ', '-').replace('\n', '')
                    url = f"{url}#{title_clean}"
                
            chapters.append(url)
            
        # Deduplicar preservando a ordem
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
        
        try:
            # A url do capítulo deve ignorar a âncora para buscar o HTML real
            clean_url = chapter_url.split('#')[0]
            html = self._fetch_html(clean_url)
            
            if "Breve Manutenção" in html or "em manutenção" in html.lower():
                logger.error(f"[{self.name}] Site em manutenção")
                raise Exception("O site Pluma Comics está em manutenção no momento.")
                
            # Limpa escapes comuns de JSON gerado pelo Next.js
            html_clean = html.replace('\\/', '/').replace('\\u002F', '/').replace('\\u0026', '&')
            
            import re
            # Busca todas as URLs de imagem (absolutas) no HTML, incluindo parâmetros (ex: ?expires=...&sig=...)
            matches = re.finditer(r'(https?://[^\s"\'`\\]+\.(?:jpg|jpeg|png|webp|avif)(?:\?[^\s"\'`\\]+)?)', html_clean)
            
            images = []
            seen = set()
            for m in matches:
                src = m.group(1)
                # Filtra apenas imagens válidas de capítulos, ignorando branding
                if ('cdn.' in src or '/chapters/' in src or '/cap-' in src) and not any(x in src.lower() for x in ['logo', 'icon', 'cover', 'branding', 'banner', 'avatar']):
                    if src not in seen:
                        seen.add(src)
                        images.append(src)
                        
            # Tenta fallback para imgs normais caso não encontre via regex no JSON
            if not images:
                soup = BeautifulSoup(html, 'html.parser')
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and ('cdn.' in src or '/chapters/' in src or '/cap-' in src) and not any(x in src.lower() for x in ['logo', 'icon', 'cover', 'branding', 'banner']):
                        if src.startswith('/'):
                            src = f"https://plumacomics.cloud{src}"
                        if src not in seen:
                            seen.add(src)
                            images.append(src)
                logger.error(f"[{self.name}] Nenhuma imagem encontrada no HTML")
                raise Exception("O capítulo não possui imagens acessíveis")
                
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar imagens do capítulo: {e}")
            raise Exception(f"Falha ao obter dados do capítulo: {e}")

