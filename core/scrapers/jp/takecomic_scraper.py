import os
import re
import json
import time
import io
import threading
import logging
import xml.etree.ElementTree as ET
import urllib.request
from typing import List, Tuple, Optional
from PIL import Image
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_takecomic_browser_lock = threading.Lock()

class TakeComicScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "TakeComic"
        self.base_url = "https://takecomic.jp"
        self.credentials = None
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Referer': 'https://takecomic.jp/'
        })

    def _get_credentials(self) -> Tuple[str, str]:
        """Obtém as credenciais fornecidas na chamada ou nas configurações salvas pelo usuário."""
        email, password = "", ""
        if self.credentials and len(self.credentials) == 2:
            email, password = self.credentials[0] or "", self.credentials[1] or ""

        if not email or not password:
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = email or settings.load("takecomic_email", "")
                password = password or settings.load("takecomic_password", "")
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao carregar credenciais das configurações: {e}")

        return email.strip(), password.strip()

    def _extract_ids(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai (series_id, episode_id) da URL informada.
        Exemplos:
          - https://takecomic.jp/series/756cda78bfb04/new -> ('756cda78bfb04', None)
          - https://takecomic.jp/episodes/7ff33017bf887 -> (None, '7ff33017bf887')
        """
        clean_url = url.split('?')[0].rstrip('/')
        parts = [p for p in clean_url.split('/') if p]

        series_id = None
        episode_id = None

        if "series" in parts:
            idx = parts.index("series")
            if idx + 1 < len(parts):
                series_id = parts[idx + 1]
        elif "episodes" in parts:
            idx = parts.index("episodes")
            if idx + 1 < len(parts):
                episode_id = parts[idx + 1]

        return series_id, episode_id

    def get_chapters(self, series_url: str) -> List[str]:
        """
        Retorna a lista de URLs dos capítulos em ordem cronológica (ascendente).
        """
        logger.info(f"[{self.name}] Buscando capítulos de: {series_url}")
        series_id, episode_id = self._extract_ids(series_url)

        # Se for uma URL direta de episódio único
        if episode_id:
            logger.info(f"[{self.name}] URL de episódio único detectada: {series_url}")
            return [series_url]

        if not series_id:
            logger.error(f"[{self.name}] ID da série não identificado na URL: {series_url}")
            return []

        # Tentar obter lista via feed RSS oficial da série
        rss_url = f"{self.base_url}/series/{series_id}/rss"
        try:
            req = urllib.request.Request(rss_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is not None:
                items = channel.findall("item")
                if items:
                    episodes = []
                    for it in items:
                        title = it.find("title").text if it.find("title") is not None else ""
                        link = it.find("link").text if it.find("link") is not None else ""
                        clean_link = link.split('?')[0].rstrip('/')
                        # Extrai o número do capítulo a partir do título (ex: "19話" -> 19)
                        m = re.search(r'(\d+(?:\.\d+)?)', title)
                        num = m.group(1) if m else "0"
                        episodes.append({
                            'url': f"{clean_link}?chapter={num}",
                            'num': float(num)
                        })

                    # Ordena do primeiro ao último (ascendente)
                    episodes.sort(key=lambda x: x['num'])
                    result = [ep['url'] for ep in episodes]
                    logger.info(f"[{self.name}] Encontrados {len(result)} capítulos via feed RSS.")
                    return result
        except Exception as e:
            logger.warning(f"[{self.name}] Não foi possível obter capítulos via RSS ({e}). Tentando página HTML...")

        # Fallback: raspar HTML da página da série
        try:
            page_url = f"{self.base_url}/series/{series_id}/1"
            req = urllib.request.Request(page_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode('utf-8')

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            seen = set()
            episodes = []

            for a in soup.find_all("a", href=True):
                href = a['href']
                if '/episodes/' in href and href not in seen:
                    seen.add(href)
                    text = a.get_text(" ", strip=True)
                    m = re.search(r'(\d+(?:\.\d+)?)', text)
                    num = m.group(1) if m else "0"
                    clean_href = href.split('?')[0].rstrip('/')
                    full_link = clean_href if clean_href.startswith('http') else f"{self.base_url}{clean_href}"
                    episodes.append({
                        'url': f"{full_link}?chapter={num}",
                        'num': float(num)
                    })

            episodes.sort(key=lambda x: x['num'])
            result = [ep['url'] for ep in episodes]
            logger.info(f"[{self.name}] Encontrados {len(result)} capítulos via HTML.")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao buscar capítulos da série: {e}")
            return []

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        """
        Retorna a lista de representações de imagens para o capítulo.
        No TakeComic o download completo e decodificação ocorrem em download_chapter.
        """
        return [f"{chapter_url}#page_{i+1}" for i in range(25)]

    def _descramble_image(self, img_bytes: bytes, scramble_str: str) -> bytes:
        """
        Reorganiza a grade de blocos 4x4 embaralhada da Comici/TakeComic usando Pillow.
        """
        src_img = Image.open(io.BytesIO(img_bytes))
        W, H = src_img.size
        cols = 4
        rows = 4
        tile_w = W // cols
        tile_h = H // rows

        ai = []
        for e in range(cols):
            for t in range(rows):
                ai.append((e, t))

        order = json.loads(scramble_str)
        p = [ai[int(x)] for x in order]

        dst_img = Image.new(src_img.mode, (W, H))
        u = 0
        for dst_col in range(cols):
            for dst_row in range(rows):
                src_col, src_row = p[u]
                src_box = (src_col * tile_w, src_row * tile_h, (src_col + 1) * tile_w, (src_row + 1) * tile_h)
                tile = src_img.crop(src_box)
                dst_pos = (dst_col * tile_w, dst_row * tile_h)
                dst_img.paste(tile, dst_pos)
                u += 1

        buf = io.BytesIO()
        dst_img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def download_chapter(self, chapter_url: str, output_dir: str, chapter_name: str, max_workers: int = 5) -> int:
        """
        Acessa a página do capítulo com sessão persistente autenticada no Playwright,
        intercepta a API contentsInfo e decodifica cada imagem salva.
        """
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)

        email, password = self._get_credentials()
        profile_dir = os.path.join(os.path.expanduser("~"), ".gemini", "readstitch_takecomic_browser")
        os.makedirs(profile_dir, exist_ok=True)

        from playwright.sync_api import sync_playwright

        with _takecomic_browser_lock:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="chrome",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.pages[0] if context.pages else context.new_page()

                # Verificar se precisa realizar login
                if email and password:
                    try:
                        page.goto(f"{self.base_url}/api/auth/session", wait_until="domcontentloaded")
                        is_logged_in = False
                        try:
                            data = json.loads(page.inner_text("body"))
                            if data.get('user'):
                                is_logged_in = True
                        except Exception:
                            pass

                        if not is_logged_in:
                            logger.info(f"[{self.name}] Realizando login para a conta {email}...")
                            page.goto(f"{self.base_url}/auth/signin", wait_until="domcontentloaded")
                            time.sleep(2)
                            page.fill("input[name='username']", email)
                            page.fill("input[name='password']", password)
                            page.click("button[type='submit']")
                            time.sleep(4)
                    except Exception as e:
                        logger.warning(f"[{self.name}] Erro ao verificar/executar login: {e}")

                # Capturar chamadas contentsInfo
                pages_info = []
                def on_response(res):
                    if "contentsInfo" in res.url:
                        try:
                            d = res.json()
                            if d.get('result'):
                                pages_info.extend(d['result'])
                        except Exception:
                            pass

                page.on("response", on_response)

                clean_chapter_url = chapter_url.split('?')[0]
                logger.info(f"[{self.name}] Carregando visualizador para {clean_chapter_url}...")
                page.goto(clean_chapter_url, wait_until="networkidle", timeout=60000)
                time.sleep(5)

                if not pages_info:
                    # Rolar a página para forçar carregamento
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)

                cookies = context.cookies()
                context.close()

        if not pages_info:
            logger.error(f"[{self.name}] Nenhuma página capturada para {chapter_url}. Verifique se o capítulo exige login/pontos.")
            return 0

        # Preparar sessão HTTP para download das imagens com os cookies da sessão
        import requests
        req_session = requests.Session()
        req_session.headers.update({
            'User-Agent': self.headers['User-Agent'],
            'Referer': clean_chapter_url
        })
        for c in cookies:
            req_session.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path'])

        # Ordenar páginas
        pages_info.sort(key=lambda p: p.get('sort', 0))

        saved_count = 0
        for idx, page_data in enumerate(pages_info):
            img_url = page_data.get('imageUrl')
            if not img_url:
                continue

            try:
                resp = req_session.get(img_url, timeout=30)
                if resp.status_code == 200 and resp.content:
                    scramble_str = page_data.get('scramble')
                    if scramble_str:
                        clean_bytes = self._descramble_image(resp.content, scramble_str)
                    else:
                        clean_bytes = resp.content

                    filename = f"{idx+1:03d}.jpg"
                    filepath = os.path.join(target_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(clean_bytes)
                    saved_count += 1
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao baixar página {idx+1}: {e}")

        logger.info(f"[{self.name}] Salvas {saved_count} páginas em {target_dir}")
        return saved_count
