import urllib.request
import urllib.parse
import re
import logging
from bs4 import BeautifulSoup
from typing import List, Tuple
from core.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class HanamiHeavenScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Hanami Heaven"
        self.base_url = "https://hanamiheaven.org"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
            'Cookie': 'age_verified=yes'
        })
        self._headers = self.headers

    def _normalize_series_url(self, raw_url: str) -> Tuple[str, bool, str]:
        """
        Normaliza a URL recebida, detectando se é um capítulo direto ou uma série.
        Retorna (series_url, is_chapter, clean_input_url).
        """
        clean = raw_url.strip().split('?')[0].split('#')[0].rstrip('/')
        parts = [p for p in urllib.parse.urlparse(clean).path.strip('/').split('/') if p]
        is_chapter = False
        series_url = clean + '/'

        if len(parts) >= 2 and parts[0] in ('manga', 'series', 'obra'):
            series_slug = parts[1]
            if len(parts) >= 3 and re.search(r'cap|ch|episode|ep', parts[2], re.IGNORECASE):
                is_chapter = True
                series_url = f"{self.base_url}/manga/{series_slug}/"

        return series_url, is_chapter, clean + '/'

    def get_chapters(self, series_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        target_series_url, is_chapter, clean_input_url = self._normalize_series_url(series_url)
        chapters = []
        soup = None
        html = ""

        # 1. Tenta extrair diretamente do HTML da página da série
        try:
            req = urllib.request.Request(target_series_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                for item in soup.select('li.wp-manga-chapter a'):
                    href = item.get('href')
                    if href and href != '#' and href not in chapters:
                        chapters.append(href)
        except Exception as e:
            logger.warning(f"[{self.name}] Falha ao buscar capítulos inline: {e}")

        # 2. Se não encontrou, tenta via endpoint POST ajax/chapters/ (padrão Madara)
        if not chapters:
            try:
                ajax_url = target_series_url.rstrip('/') + '/ajax/chapters/'
                req = urllib.request.Request(ajax_url, method='POST', headers=self.headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    ajax_html = resp.read().decode('utf-8', errors='ignore')
                    ajax_soup = BeautifulSoup(ajax_html, 'html.parser')
                    for item in ajax_soup.select('li.wp-manga-chapter a'):
                        href = item.get('href')
                        if href and href != '#' and href not in chapters:
                            chapters.append(href)
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao buscar capítulos via ajax/chapters/: {e}")

        # 3. Se ainda não encontrou e temos a página, tenta admin-ajax com manga_id
        if not chapters and soup:
            manga_id = None
            holder = soup.find('div', id='manga-chapters-holder')
            if holder and holder.get('data-id'):
                manga_id = holder.get('data-id')
            if not manga_id:
                manga_input = soup.find('input', class_='wp-manga-post-id')
                if manga_input:
                    manga_id = manga_input.get('value')
            if not manga_id:
                match = re.search(r'manga_id\s*=\s*["\'](\d+)["\']', html)
                if match:
                    manga_id = match.group(1)

            if manga_id:
                try:
                    admin_ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"
                    data = urllib.parse.urlencode({
                        'action': 'manga_get_chapters',
                        'manga': manga_id
                    }).encode('utf-8')
                    req = urllib.request.Request(admin_ajax_url, data=data, method="POST", headers=self.headers)
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        admin_soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')
                        for item in admin_soup.select('li.wp-manga-chapter a'):
                            href = item.get('href')
                            if href and href != '#' and href not in chapters:
                                chapters.append(href)
                except Exception as e:
                    logger.warning(f"[{self.name}] Falha ao buscar capítulos via admin-ajax: {e}")

        # Fallback: se era um capítulo direto e nenhuma lista foi encontrada, retorna o próprio capítulo
        if not chapters and is_chapter:
            logger.info(f"[{self.name}] Usando capítulo individual detectado na URL: {clean_input_url}")
            return [clean_input_url]

        # Ordenar capítulos em ordem cronológica ascendente (Capítulo 1 ao último)
        def extract_num(u: str) -> float:
            m = re.search(r'(?:capitulo|chapter|cap|ch)[-_/]?(\d+(?:[.-]\d+)?)', u, re.IGNORECASE)
            if m:
                val = m.group(1).replace('-', '.')
                try:
                    return float(val)
                except ValueError:
                    pass
            m = re.search(r'(\d+(?:\.\d+)?)', u)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
            return 0.0

        chapters.sort(key=extract_num)

        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        return chapters

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching images for chapter: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            # Imagens costumam ficar na div reading-content ou .wp-manga-chapter-img
            img_tags = soup.select('.reading-content img, .wp-manga-chapter-img, .page-break img')
            for img in img_tags:
                src = (
                    img.get('data-src')
                    or img.get('data-lazy-src')
                    or img.get('data-original')
                    or img.get('data-full-url')
                    or img.get('data-wpfc-original-src')
                    or img.get('src')
                )
                if not src:
                    continue
                src = src.strip()
                if src.startswith('data:image'):
                    srcset = img.get('srcset') or img.get('data-srcset')
                    if srcset:
                        first = srcset.split(',')[0].strip().split(' ')[0]
                        if first and not first.startswith('data:'):
                            src = first
                        else:
                            continue
                    else:
                        continue
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = f"{self.base_url}{src}"
                if src not in images:
                    images.append(src)
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens no capítulo.")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar página do capítulo: {e}")
            return []
