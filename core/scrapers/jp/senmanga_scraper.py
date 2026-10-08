import urllib.request
import urllib.parse
import json
import re
import logging
from typing import List, Tuple, Optional
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SenMangaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Sen Manga"
        self.base_url = "https://raw.senmanga.com"
        self.api_url = "https://raw.senmanga.com/api"
        self.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://raw.senmanga.com/'
        })

    def _extract_slug(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai (manga_slug, chapter_part) a partir da URL fornecida.
        Exemplos:
          - https://raw.senmanga.com/gedou-tenisha-no-harem-dungeon-seisakuki
          - https://raw.senmanga.com/gedou-tenisha-no-harem-dungeon-seisakuki/18
          - https://raw.senmanga.com/gedou-tenisha-no-harem-dungeon-seisakuki/chapter-18.293431
        """
        clean_url = url.split('?')[0].strip('/')
        # Remove esquema e domínio
        clean_url = re.sub(r'^https?://[^/]+/?', '', clean_url)
        parts = [p for p in clean_url.split('/') if p]

        if not parts:
            return None, None

        manga_slug = parts[0]
        chapter_part = parts[1] if len(parts) > 1 else None
        return manga_slug, chapter_part

    def get_chapters(self, series_url: str) -> List[str]:
        """
        Retorna a lista de URLs dos capítulos em ordem cronológica (ascendente).
        """
        logger.info(f"[{self.name}] Buscando capítulos de: {series_url}")
        manga_slug, chapter_part = self._extract_slug(series_url)
        if not manga_slug:
            logger.error(f"[{self.name}] Slug do mangá não encontrado na URL: {series_url}")
            return []

        # Se a URL já for um capítulo direto
        if chapter_part:
            logger.info(f"[{self.name}] URL de capítulo único detectada: {series_url}")
            return [series_url]

        api_endpoint = f"{self.api_url}/manga/{manga_slug}"
        req = urllib.request.Request(api_endpoint, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar dados da série em {api_endpoint}: {e}")
            raise Exception(f"Falha ao obter dados da série no Sen Manga: {e}")

        chapters = data.get('chapterList', [])
        if not chapters:
            logger.warning(f"[{self.name}] Nenhum capítulo encontrado para {manga_slug}")
            return []

        def parse_chapter_number(c):
            val = c.get('slug') or c.get('number') or '0'
            try:
                return float(val)
            except Exception:
                m = re.search(r'(\d+(?:\.\d+)?)', str(val))
                return float(m.group(1)) if m else 0.0

        # Ordenar do primeiro ao último capítulo
        chapters.sort(key=parse_chapter_number)

        result = []
        for c in chapters:
            slug = c.get('slug') or c.get('number') or ''
            chap_url_param = c.get('url') or ''
            # Monta a URL com os parâmetros ?url e ?chapter para facilitar a detecção no Downloader
            chap_url = f"{self.base_url}/{manga_slug}/chapter-{slug}?url={chap_url_param}&chapter={slug}"
            result.append(chap_url)

        logger.info(f"[{self.name}] Encontrados {len(result)} capítulos para {manga_slug}")
        return result

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        """
        Retorna a lista de URLs das imagens das páginas de um capítulo.
        """
        logger.info(f"[{self.name}] Buscando páginas de: {chapter_url}")
        parsed = urllib.parse.urlparse(chapter_url)
        qs = urllib.parse.parse_qs(parsed.query)

        manga_slug, chapter_part = self._extract_slug(chapter_url)
        if not manga_slug:
            logger.error(f"[{self.name}] Não foi possível identificar o mangá em {chapter_url}")
            return []

        # Tentar obter read_id diretamente do parâmetro ?url=
        read_id = qs.get('url', [None])[0]

        # Se não vier na query string, consultar a API da série para descobrir o read_id
        if not read_id:
            manga_api = f"{self.api_url}/manga/{manga_slug}"
            req = urllib.request.Request(manga_api, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                
                chap_clean = (chapter_part or '').replace('chapter-', '')
                for c in data.get('chapterList', []):
                    if (c.get('slug') == chap_clean or 
                        c.get('url') == chapter_part or 
                        c.get('number') == chap_clean):
                        read_id = c.get('url')
                        break
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao buscar metadados para resolver read_id: {e}")

            if not read_id:
                read_id = chapter_part

        if not read_id:
            logger.error(f"[{self.name}] Identificador de leitura (read_id) não encontrado.")
            return []

        read_api = f"{self.api_url}/read/{manga_slug}/{read_id}"
        req = urllib.request.Request(read_api, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar páginas em {read_api}: {e}")
            raise Exception(f"Falha ao carregar páginas do capítulo no Sen Manga: {e}")

        pages = data.get('pages', [])
        logger.info(f"[{self.name}] Encontradas {len(pages)} páginas no capítulo.")
        return pages
