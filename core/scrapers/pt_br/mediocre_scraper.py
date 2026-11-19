import urllib.request
import urllib.error
import json
import logging
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MediocreScraper(BaseScraper):
    """Scraper para o site MediocreToons / LaranjaToons (requer login)."""
    
    @property
    def name(self):
        return "LaranjaToons"

    def __init__(self):
        super().__init__()
        self.base_url = "https://laranjatoons.com"
        self.api_url = "https://api.laranjatoons.com"
        self.cdn_url = "https://cdn.laranjatoons.com"
        self.headers.update({
            'Accept': 'application/json',
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
        })
        self.token = None

    def login(self, email, password):
        """Autentica na API da LaranjaToons e salva o token."""
        logger.info(f"[{self.name}] Tentando login com {email}")
        try:
            url = f"{self.api_url}/auth/login"
            payload = {
                "email": email.strip(),
                "senha": password.strip()
            }
            data = json.dumps(payload).encode('utf-8')
            
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                
                token = (
                    resp_data.get('access_token')
                    or resp_data.get('token')
                    or (resp_data.get('data') or {}).get('access_token')
                    or (resp_data.get('data') or {}).get('token')
                )
                
                if not token:
                    raise Exception("Token não retornado pela API")
                    
                self.token = token
                self.headers['Authorization'] = f"Bearer {token}"
                
                logger.info(f"[{self.name}] Login efetuado com sucesso!")
                return True
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            logger.error(f"[{self.name}] Falha no login HTTPError {e.code}: {error_body}")
            if e.code == 401 or e.code == 400:
                raise Exception("Falha de autenticação: E-mail ou Senha inválidos.")
            elif e.code in (502, 503, 521, 522):
                raise Exception(f"O site {self.name} está em manutenção ou fora do ar no momento. Tente novamente mais tarde.")
            raise Exception(f"Erro ao conectar com {self.name} (HTTP {e.code}).")
        except Exception as e:
            logger.error(f"[{self.name}] Falha no login Exception: {e}")
            raise Exception(f"Erro inesperado ao conectar com {self.name}: {e}")

    def has_active_login(self):
        return self.token is not None

    def _fetch_api(self, url):
        if not self.has_active_login():
            raise Exception(f"A {self.name} requer login obrigatório. Faça login no aplicativo primeiro.")
            
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as response:
                data = response.read().decode('utf-8', errors='ignore')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8', errors='ignore')
                error_json = json.loads(error_body)
                msg = error_json.get('message', str(e))
                raise Exception(f"API Error ({e.code}): {msg}")
            except:
                raise Exception(f"API Error ({e.code}): {e.reason}")

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        if not self.has_active_login():
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("mediocre_email")
                password = settings.load("mediocre_password")
                
                if not email or not password:
                    raise Exception("Credenciais não configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso'.")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")
        
        parts = [p for p in series_url.split('?')[0].split('/') if p]
        
        try:
            obra_id = None
            if 'obra' in parts:
                idx = parts.index('obra')
                if idx + 1 < len(parts):
                    cand = parts[idx + 1].split('-')[0]
                    if cand.isdigit():
                        obra_id = cand
            elif 'obras' in parts:
                idx = parts.index('obras')
                if idx + 1 < len(parts):
                    cand = parts[idx + 1].split('-')[0]
                    if cand.isdigit():
                        obra_id = cand
            
            if not obra_id:
                nums = [p.split('-')[0] for p in parts if p.split('-')[0].isdigit()]
                if nums:
                    obra_id = nums[0]
                else:
                    raise Exception("URL inválida ou ID da obra não encontrado.")
            
            details_url = f"{self.api_url}/obras/{obra_id}"
            details_data = self._fetch_api(details_url)

            data_obj = details_data
            if isinstance(details_data, dict):
                if 'data' in details_data and isinstance(details_data['data'], dict) and 'capitulos' in details_data['data']:
                    data_obj = details_data['data']

            chapters_data = data_obj.get('capitulos', [])
            
            if not chapters_data:
                logger.warning(f"[{self.name}] Nenhum capítulo encontrado.")
                return []
                
            all_chapters = []
            for item in chapters_data:
                chap_id = item.get('cap_id') or item.get('id')
                chap_num = item.get('cap_num') or item.get('numero')
                url = f"{self.base_url}/obra/{obra_id}/capitulo/{chap_num}#chapterId={chap_id}"
                all_chapters.append(url)
                
            logger.info(f"[{self.name}] Found {len(all_chapters)} chapters")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao processar a série: {e}")
            raise Exception(f"Falha ao obter a lista de capítulos: {e}")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        if not self.has_active_login():
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("mediocre_email")
                password = settings.load("mediocre_password")
                
                if not email or not password:
                    raise Exception("Credenciais não configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso'.")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")

        try:
            chapter_id = None
            if '#chapterId=' in chapter_url:
                fragment = chapter_url.split('#chapterId=')[1]
                chapter_id = fragment.split('&')[0].split('/')[0]
            elif '/capitulo/' in chapter_url:
                parts = [p for p in chapter_url.split('?')[0].split('#')[0].split('/') if p]
                if 'capitulo' in parts:
                    idx = parts.index('capitulo')
                    if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                        chapter_id = parts[idx + 1]
            if not chapter_id:
                nums = [p for p in chapter_url.split('?')[0].split('#')[0].split('/') if p.isdigit()]
                if nums:
                    chapter_id = nums[-1]
                else:
                    raise Exception("Chapter ID ausente na URL")
                
            api_chap_url = f"{self.api_url}/capitulos/{chapter_id}"
            chap_data = self._fetch_api(api_chap_url)
            
            data = chap_data
            if isinstance(chap_data, dict) and 'data' in chap_data and isinstance(chap_data['data'], dict):
                data = chap_data['data']

            obra_id = (data.get('obra') or {}).get('id') or data.get('obr_id') or data.get('obra_id') or data.get('obraId')
            cap_num = data.get('cap_num') or data.get('numero')
            cap_uuid = data.get('cap_uuid') or data.get('uuid')
            
            if not cap_uuid:
                raise Exception("Metadados do capítulo incompletos na API (uuid ausente).")
                
            # URLs candidatas do JSON no CDN
            cdn_candidates = []
            if obra_id is not None and cap_num is not None:
                cdn_candidates.append(f"{self.cdn_url}/obras/{obra_id}/capitulos/{cap_num}/{cap_uuid}.json")
            cdn_candidates.append(f"{self.cdn_url}/capitulos/{cap_uuid}.json")
            
            pages_data = None
            last_err = None
            for cdn_url in cdn_candidates:
                try:
                    req = urllib.request.Request(
                        cdn_url,
                        headers={
                            'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                            'Referer': f"{self.base_url}/",
                            'Origin': self.base_url
                        }
                    )
                    with urllib.request.urlopen(req) as resp:
                        pages_data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                    if pages_data:
                        break
                except Exception as err:
                    last_err = err
                    continue

            if not pages_data:
                raise Exception(f"O capítulo não possui imagens acessíveis: {last_err or 'vazio'}")
                
            images = []
            for p in pages_data:
                if isinstance(p, dict):
                    img_url = p.get('url') or p.get('src')
                elif isinstance(p, str):
                    img_url = p
                else:
                    img_url = None

                if img_url:
                    if img_url.startswith('http'):
                        images.append(img_url)
                    else:
                        images.append(f"{self.cdn_url}/{img_url.lstrip('/')}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Falha ao obter imagens: {e}")
            raise Exception(f"Falha ao obter imagens do capítulo: {e}")
