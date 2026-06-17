import re
import json
import urllib.request
import urllib.parse
import logging
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SafireScanScraper(BaseScraper):
    """Scraper para o site Safire Scan (hospedado no Blogger)."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.safirescan.site"
        self.generic_tags = {
            'chapter', 'series', 'project', 'manhwa', 'manhua', 'manga', 'drama', 
            'fantasy', 'romance', 'josei', 'shoujo', 'shounen', 'seinen', 'ongoing', 
            'completed', 'português', 'portugues', 'nsfw', 'smut', 'mature', 'e', 'q', 
            'c', 'o', 'p', 'r', 'l', 'comedy', 'mystery', 'historical', 'reverse harem', 
            'dropped', 'one-shot', 'safire scan', 'por aine', 'hentai', 'isekai'
        }

    @property
    def name(self):
        return "Safire Scan"

    def _fetch_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='ignore')

    def _fetch_json(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))

    def _get_post_id(self, html):
        # Allow quotes around postId (e.g. 'postId': '123')
        match = re.search(r'[\'"]?post(?:Id|ID)[\'"]?\s*[:=]\s*[\'"]?(\d+)[\'"]?', html, re.IGNORECASE)
        if match:
            return match.group(1)
            
        # Tenta procurar por um número de 19 digitos (tamanho comum do postID do blogger)
        match = re.search(r'[\'"]?blog(?:Id|ID)[\'"]?\s*[:=]\s*[\'"]?\d+[\'"]?.*?[\'"]?post(?:Id|ID)[\'"]?\s*[:=]\s*[\'"]?(\d+)[\'"]?', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
            
        # Alternativa
        match = re.search(r'name="postId" value="(\d+)"', html)
        if match:
            return match.group(1)
            
        return None

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Buscando capítulos em: {series_url}")
        
        # Se for uma URL de label (ex: /search/label/Nome), usa o label diretamente
        if '/search/label/' in series_url:
            label = series_url.split('/search/label/')[-1].split('?')[0]
            label = urllib.parse.unquote(label)
            return self._get_chapters_by_label(label)

        html = self._fetch_html(series_url)
        post_id = self._get_post_id(html)
        
        if not post_id:
            logger.error(f"[{self.name}] Não foi possível encontrar o ID do post na página.")
            raise Exception("Não foi possível encontrar o ID da série")

        logger.info(f"[{self.name}] ID do post encontrado: {post_id}")
        
        # Pega as informações do post via Feed da API do Blogger
        feed_url = f"{self.base_url}/feeds/posts/default/{post_id}?alt=json"
        try:
            post_data = self._fetch_json(feed_url)
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar dados do post: {e}")
            raise Exception("Erro ao comunicar com a API do site.")

        categories = post_data.get('entry', {}).get('category', [])
        labels = [c['term'] for c in categories]
        logger.info(f"[{self.name}] Labels encontradas: {labels}")

        # Filtra labels genéricas ou decimais (como notas 8.1, 7.9)
        candidate_labels = []
        for lbl in labels:
            lbl_lower = lbl.lower()
            if lbl_lower in self.generic_tags:
                continue
            if re.match(r'^\d+(\.\d+)?$', lbl_lower):
                continue
            candidate_labels.append(lbl)

        if not candidate_labels:
            raise Exception("Nenhuma tag de série encontrada no post.")

        # Testa as labels candidatas para ver qual retorna capítulos
        for label in candidate_labels:
            chapters = self._get_chapters_by_label(label)
            if chapters:
                return chapters

        raise Exception("Nenhum capítulo encontrado nas labels da série.")

    def _get_chapters_by_label(self, label):
        logger.info(f"[{self.name}] Buscando capítulos pela label: {label}")
        feed_url = f"{self.base_url}/feeds/posts/default/-/{urllib.parse.quote(label)}?alt=json&max-results=9999"
        
        try:
            feed_data = self._fetch_json(feed_url)
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar feed da label {label}: {e}")
            return []

        entries = feed_data.get('feed', {}).get('entry', [])
        chapters = []
        
        for entry in entries:
            # Verifica se é um capítulo (tem a categoria 'Chapter' ou se chama 'Cap')
            cats = [c['term'].lower() for c in entry.get('category', [])]
            title = entry.get('title', {}).get('$t', '')
            
            if 'chapter' in cats or 'cap' in title.lower():
                # Encontra o link alternativo
                links = entry.get('link', [])
                alt_link = next((l['href'] for l in links if l.get('rel') == 'alternate'), None)
                if alt_link:
                    chapters.append(alt_link)
                    
        # A API do Blogger retorna os mais recentes primeiro, então revertemos para ter a ordem do 1 ao mais recente.
        chapters.reverse()
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos na label '{label}'.")
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Extraindo imagens do capítulo: {chapter_url}")
        
        html = self._fetch_html(chapter_url)
        post_id = self._get_post_id(html)
        
        content_html = ""
        
        if post_id:
            # Pega o conteúdo diretamente da API do Blogger (evita problemas com lazy loading no DOM)
            feed_url = f"{self.base_url}/feeds/posts/default/{post_id}?alt=json"
            try:
                post_data = self._fetch_json(feed_url)
                content_html = post_data.get('entry', {}).get('content', {}).get('$t', '')
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao buscar dados da API ({e}), usando o HTML da página.")
                
        if not content_html:
            # Fallback para extração direta do HTML
            soup = BeautifulSoup(html, 'html.parser')
            # O Blogger armazena o conteúdo do post na classe 'post-body'
            post_body = soup.find('div', class_='post-body')
            if post_body:
                content_html = str(post_body)
            else:
                content_html = html

        soup = BeautifulSoup(content_html, 'html.parser')
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                src = src.strip()
                # Remove imagens genéricas de layout
                if 'b16-rounded.gif' in src or 'blogger.png' in src or 'pixel.gif' in src:
                    continue
                images.append(src)
                
        if not images:
            raise Exception("Nenhuma imagem encontrada no conteúdo do capítulo.")
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens.")
        return images
