import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper


class HentaiYogaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://hentai.yoga"
        self.headers['Referer'] = 'https://hentai.yoga/'
        self.series_title = ""

    @property
    def name(self) -> str:
        return "Hentai Yoga"

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8', errors='replace')
        return BeautifulSoup(html, 'html.parser')

    def get_chapters(self, series_url: str) -> list[str]:
        # Se for link direto de um capítulo
        if "/chapter/" in series_url:
            return [series_url]

        soup = self._fetch_soup(series_url)

        # Captura o título da obra
        h1 = soup.find('h1') or soup.select_one('.post-title, .entry-title, .manga-title')
        if h1:
            title_text = h1.text.strip()
            # Limpa prefixos/sufixos comuns caso existam
            title_text = re.sub(r'^(?:Manga|Manhwa)\s+', '', title_text, flags=re.IGNORECASE)
            title_text = title_text.split('–')[0].split('-')[0].strip()
            if title_text:
                self.series_title = title_text

        # Extrai o slug da obra da URL
        m = re.search(r'/(?:manga|manhwa)/([^/?#]+)', series_url)
        slug = m.group(1) if m else series_url.rstrip('/').split('/')[-1]

        # Encontra todos os links de capítulos pertencentes a este mangá
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Garante que o link pertence à obra e é um capítulo
            if f"/{slug}/chapter/" in href:
                # Normaliza URL
                clean_href = href.split('?')[0].rstrip('/')
                if not clean_href.startswith('http'):
                    clean_href = urllib.parse.urljoin(self.base_url, clean_href)
                links.add(clean_href)

        if not links:
            # Fallback mais amplo: qualquer link com /chapter/ e o slug
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "/chapter/" in href and slug in href:
                    clean_href = href.split('?')[0].rstrip('/')
                    if not clean_href.startswith('http'):
                        clean_href = urllib.parse.urljoin(self.base_url, clean_href)
                    links.add(clean_href)

        if not links:
            raise Exception(f"Nenhum capítulo encontrado para a série em: {series_url}")

        def extract_num(url_str):
            m_num = re.search(r'chapter-(\d+(?:[.-]\d+)?)', url_str)
            if m_num:
                val = m_num.group(1).replace('-', '.')
                try:
                    return float(val)
                except ValueError:
                    pass
            return 999999.0

        return sorted(list(links), key=extract_num)

    def get_chapter_images(self, chapter_url: str) -> list[str]:
        soup = self._fetch_soup(chapter_url)

        # Seleciona imagens do capítulo
        img_elements = soup.select('img.chapter-image, .chapter-image img, #chapter-images img')
        if not img_elements:
            img_elements = soup.select('.reading-content img, .chapter-content img')
        if not img_elements:
            # Fallback para elementos de imagem da CDN do hentai.yoga ou com padrão chapter-
            img_elements = [
                img for img in soup.find_all('img')
                if img.get('src') and ('cdn.hentai.yoga' in img.get('src') or '/chapter-' in img.get('src'))
            ]

        images = []
        for img in img_elements:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
            if not src or src.startswith('data:'):
                continue

            src = src.strip()
            # Ignora logotipos, ícones, banners e placeholders
            src_lower = src.lower()
            if any(ign in src_lower for ign in ['logo', 'banner', 'icon', 'placeholder', 'avatar', 'cover']):
                continue

            # Remove parâmetros de resize da CDN (ex: ?width=800&format=webp) para obter resolução original
            if '?' in src:
                src = src.split('?')[0]

            if not src.startswith('http'):
                src = urllib.parse.urljoin(self.base_url, src)

            images.append(src)

        if not images:
            raise Exception(f"Nenhuma imagem encontrada no capítulo: {chapter_url}")

        return images
