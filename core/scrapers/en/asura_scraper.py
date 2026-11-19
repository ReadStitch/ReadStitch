import urllib.request
import urllib.parse
import re
import json
import base64
import os
import io
import logging
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

class AsuraScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "Asura Scans"
        self.base_url = "https://asurascans.com"
        self.api_url = "https://api.asurascans.com/api"
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f"{self.base_url}/",
        })
        self.credentials = None
        self._access_token = None

    def _get_access_token(self, force_refresh=False):
        if not force_refresh and self._access_token:
            self.headers["Authorization"] = f"Bearer {self._access_token}"
            self.headers["Cookie"] = f"access_token={self._access_token}"
            return self._access_token

        cache_file = os.path.join(os.path.expanduser("~"), ".asura_token_cache")
        if force_refresh:
            self._access_token = None
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception:
                    pass

        # Tenta carregar do cache se não for forçar renovação
        if not force_refresh and os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    self._access_token = f.read().strip()
                if self._access_token:
                    self.headers["Authorization"] = f"Bearer {self._access_token}"
                    self.headers["Cookie"] = f"access_token={self._access_token}"
                    return self._access_token
            except Exception:
                pass

        # Tentar carregar credenciais das configurações se não foram passadas pelo construtor/GUI
        if not self.credentials:
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("asura_email")
                password = settings.load("asura_password")
                if email and password:
                    self.credentials = (email.strip(), password.strip())
            except Exception:
                pass

        if not self.credentials:
            logger.info(f"[{self.name}] Nenhuma credencial de acesso foi preenchida para a Asura.")
            return None

        email, password = self.credentials
        if not email or not password:
            return None

        logger.info(f"[{self.name}] Autenticando na API do Asura Scans por debaixo dos panos (sem abrir navegador)...")
        try:
            login_url = f"{self.api_url}/auth/login"
            payload = json.dumps({"email": email, "password": password}).encode('utf-8')
            headers = self.headers.copy()
            headers["Content-Type"] = "application/json"
            
            req = urllib.request.Request(
                login_url, 
                data=payload, 
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                response_data = response.read().decode('utf-8')
                cookies = response.headers.get_all('Set-Cookie')
                
                # Procurar o token nos cookies
                if cookies:
                    for cookie in cookies:
                        if 'access_token=' in cookie:
                            match = re.search(r'access_token=([^;]+)', cookie)
                            if match:
                                self._access_token = match.group(1)
                                break
                
                # Se não achou no cookie, procurar no JSON de resposta
                if not self._access_token:
                    try:
                        json_resp = json.loads(response_data)
                        if 'data' in json_resp and 'access_token' in json_resp['data']:
                            self._access_token = json_resp['data']['access_token']
                    except Exception:
                        pass
                
                if self._access_token:
                    logger.info(f"[{self.name}] Login bem sucedido! Token de acesso capturado via API.")
                    with open(cache_file, "w") as f:
                        f.write(self._access_token)
                    self.headers["Authorization"] = f"Bearer {self._access_token}"
                    self.headers["Cookie"] = f"access_token={self._access_token}"
                    return self._access_token
                else:
                    logger.warning(f"[{self.name}] Login bem sucedido, mas não foi possível encontrar o token na resposta.")
                    
        except Exception as e:
            try:
                error_msg = e.read().decode('utf-8')
                logger.error(f"[{self.name}] Erro ao fazer login na API: {error_msg}")
            except Exception:
                logger.error(f"[{self.name}] Erro de conexão ao tentar fazer login na API: {e}")

        return None

    def get_chapters(self, series_url):
        """
        Fetches the series page and extracts a list of all chapter URLs.
        Returns a sorted list of absolute chapter URLs.
        """
        series_url = series_url.strip()
        series_url = series_url.replace("asuracomic.net", "asurascans.com").replace("asuracomics.com", "asurascans.com")

        if "/chapter/" in series_url:
            return [series_url]
            
        # Tenta carregar token (do cache ou logado) para garantir acesso a links de assinantes
        self._get_access_token()
            
        try:
            req = urllib.request.Request(series_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                final_url = response.geturl()
                html = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            raise Exception(f"Failed to fetch series page: {e}")

        # Extrair o slug limpo sem query params
        path = urllib.parse.urlparse(final_url).path.strip('/')
        parts = [p for p in path.split('/') if p]
        
        if not parts:
            logger.warning(f"[{self.name}] URL da série redirecionou para a home. O link pode não existir.")
            return []
            
        slug = parts[-1]
        
        # Regex flexível para achar os links do capítulo no HTML renderizado SSR
        pattern = r'href=[\'\"](/(?:comics|series)/' + re.escape(slug) + r'(?:-[a-fA-F0-9]+)?/chapter/[^\'\"]+)[\'\"]'
        links = set(re.findall(pattern, html))
        
        # Se não encontrou links com o slug exato, tenta com o slug original
        if not links:
            original_slug = [p for p in urllib.parse.urlparse(series_url).path.strip('/').split('/') if p][-1]
            clean_slug = re.sub(r'-[a-fA-F0-9]{8}$', '', original_slug)
            pattern = r'href=[\'\"](/(?:comics|series)/' + re.escape(clean_slug) + r'(?:-[a-fA-F0-9]+)?/chapter/[^\'\"]+)[\'\"]'
            links = set(re.findall(pattern, html))
            
        # Fallback genérico para qualquer link de capítulo na página
        if not links:
            pattern = r'href=[\'\"]((?:https?://[^/]+)?/(?:comics|series)/[^/]+/chapter/[^\'\"]+)[\'\"]'
            for match in re.findall(pattern, html):
                if match.startswith('http'):
                    links.add(urllib.parse.urlparse(match).path)
                else:
                    links.add(match)

        def extract_num(path):
            match = re.search(r'chapter(?:-|\/)(\d+(?:\.\d+)?)', path)
            return float(match.group(1)) if match else 0
            
        sorted_links = sorted(list(links), key=extract_num)
        return [self.base_url + (l if l.startswith('/') else '/' + l) for l in sorted_links]

    def _unscramble_image(self, img_url, page_data):
        if not HAS_PILLOW:
            logger.warning(f"[{self.name}] Pillow não instalado! Imagem embaralhada não pôde ser reconstruída. Salvando original...")
            return img_url

        try:
            # Baixa a imagem embaralhada em memória utilizando os cabeçalhos autenticados
            headers = self.headers.copy()
            headers['Referer'] = f"{self.base_url}/"
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                img_data = response.read()
            
            source = Image.open(io.BytesIO(img_data)).convert('RGBA')
            tileCols = page_data.get('tileCols', 1)
            tileRows = page_data.get('tileRows', 1)
            tiles = page_data.get('tiles', [])
            
            if not tiles or tileCols <= 1 or tileRows <= 1:
                return img_url # Não é embaralhada

            tileW = source.width // tileCols
            tileH = source.height // tileRows
            
            output = Image.new('RGBA', (source.width, source.height))
            
            for w, j in enumerate(tiles):
                srcCol = w % tileCols
                srcRow = w // tileCols
                dstCol = j % tileCols
                dstRow = j // tileCols
                
                srcBox = (srcCol * tileW, srcRow * tileH, (srcCol + 1) * tileW, (srcRow + 1) * tileH)
                dstBox = (dstCol * tileW, dstRow * tileH, (dstCol + 1) * tileW, (dstRow + 1) * tileH)
                
                tile = source.crop(srcBox)
                output.paste(tile, dstBox)
                
            # Salva o resultado em base64 usando Data URI
            buffer = io.BytesIO()
            output.save(buffer, format="WEBP", quality=100)
            b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/webp;base64,{b64_str}"
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao desembaralhar imagem {img_url}: {e}")
            return img_url

    def get_chapter_images(self, chapter_url):
        """
        Fetches the chapter page and extracts all image URLs using the API.
        """
        chapter_url = chapter_url.strip()
        chapter_url = chapter_url.replace("asuracomic.net", "asurascans.com").replace("asuracomics.com", "asurascans.com")

        path = urllib.parse.urlparse(chapter_url).path
        match = re.search(r'/(?:comics|series)/([^/]+)/chapter/([^/]+)', path)
        if not match:
            logger.error(f"[{self.name}] Formato de URL de capítulo não reconhecido.")
            return []
        
        slug = match.group(1)
        chapter_number = match.group(2)
        api_endpoint = f"{self.api_url}/series/{slug}/chapters/{chapter_number}"
        
        # Garante carregamento inicial do token
        self._get_access_token(force_refresh=False)
        
        def _fetch():
            headers = self.headers.copy()
            headers['Accept'] = 'application/json, text/plain, */*'
            headers['Referer'] = f"{self.base_url}/"
            req = urllib.request.Request(api_endpoint, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"[{self.name}] Falha na requisição API: {e}")
                return None

        logger.info(f"[{self.name}] Buscando imagens na API: {api_endpoint}")
        data = _fetch()

        # Verifica se falhou ou se veio sem páginas (indicando token expirado/capítulo protegido)
        missing_pages = (not data or 'data' not in data or 'chapter' not in data['data'] or not data['data']['chapter'].get('pages'))
        
        # Se as páginas vieram vazias mas você preencheu email/senha, o token no cache pode estar vencido/inválido.
        if missing_pages and self.credentials and self.credentials[0] and self.credentials[1]:
            logger.info(f"[{self.name}] O capítulo está protegido ou o token expirou. Renovando login automaticamente sem navegador...")
            new_token = self._get_access_token(force_refresh=True)
            if new_token:
                logger.info(f"[{self.name}] Refazendo requisição do capítulo com o novo login...")
                data = _fetch()
                
        if not data or 'data' not in data or 'chapter' not in data['data'] or not data['data']['chapter'].get('pages'):
            logger.warning(f"[{self.name}] Não foi possível carregar as imagens. Se este capítulo é exclusivo, verifique se seu email e senha têm permissão ativa na Asura Scans.")
            return []

        pages = data['data']['chapter']['pages']
        ordered = []
        
        for p in pages:
            img_url = p.get('url')
            if not img_url:
                continue
                
            if 'tiles' in p and p['tiles']:
                logger.info(f"[{self.name}] Imagem embaralhada detectada. Desembaralhando...")
                ordered.append(self._unscramble_image(img_url, p))
            else:
                ordered.append(img_url)
                
        return ordered
