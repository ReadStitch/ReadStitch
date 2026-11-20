import urllib.request
from bs4 import BeautifulSoup
from typing import List
import logging
from core.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MangaLivreBlogScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Manga Livre Blog"
        self.base_url = "https://mangalivre.blog"

    def get_chapters(self, series_url: str) -> List[str]:
        import json
        import re
        import time
        from urllib.parse import urljoin, urlencode

        chapters = []
        seen = set()

        def adicionar(html):
            pagina = BeautifulSoup(html, "html.parser")
            for a in pagina.select("a[href]"):
                href = urljoin(series_url, a["href"])
                if "/capitulo/" in href and href not in seen:
                    seen.add(href)
                    chapters.append(href)

        req = urllib.request.Request(series_url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")

        soup = BeautifulSoup(html, "html.parser")
        adicionar(html)
        botao = soup.select_one("#sr-load-chapters")

        if botao:
            config = None
            for script in soup.find_all("script"):
                m = re.search(
                    r"\bsrPerformance\s*=\s*(\{.*?\})\s*;",
                    script.get_text(), re.S
                )
                if m:
                    config = json.loads(m.group(1))
                    break

            if not config:
                raise RuntimeError("Configuração de paginação não encontrada.")

            offset = int(botao["data-offset"])
            total = int(botao["data-total"])
            endpoint = config["rest"].rstrip("/") + "/chapters/" + botao["data-manga"]
            headers = dict(self.headers)
            if config.get("nonce"):
                headers["X-WP-Nonce"] = config["nonce"]

            while offset < total:
                url = endpoint + "?" + urlencode({"offset": offset, "search": ""})
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    dados = json.load(resp)

                adicionar(dados.get("grid", "") + dados.get("list", ""))
                proximo = int(dados["offset"])
                total = int(dados["total"])
                if proximo <= offset:
                    raise RuntimeError("A paginação parou antes de terminar.")
                offset = proximo
                logger.info(f"[{self.name}] Carregados {offset} de {total}")
                time.sleep(0.5)

        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos")
        return chapters

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        logger.info(f"[{self.name}] Fetching images for chapter: {chapter_url}")
        
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            for img in soup.select('img.chapter-image'):
                src = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
                if src:
                    src = src.strip()
                    if src not in images:
                        images.append(src)
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens no capítulo.")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao carregar página do capítulo: {e}")
            return []
