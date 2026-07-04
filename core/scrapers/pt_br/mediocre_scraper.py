import urllib.request
import json
import logging
from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MediocreScraper(BaseScraper):
    """Scraper para o site MediocreToons (requer login)."""
    
    @property
    def name(self):
        return "MediocreToons"

    def __init__(self):
        super().__init__()
        self.base_url = "https://mediocrescan.com"
        self.api_url = "https://back2.mediocrescan.com"
        self.cdn_url = "https://cdn.mediocrescan.com"
        self.headers.update({
            'Accept': 'application/json',
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
            'x-app-key': 'toons-mediocre-app'
        })
        self.token = None

    def login(self, email, password):
        """Autentica na API da MediocreToons e salva o token."""
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
                
                token = resp_data.get('access_token') or resp_data.get('token')
                
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
                raise Exception("O site MediocreToons está em manutenção ou fora do ar no momento. Tente novamente mais tarde.")
            raise Exception(f"Erro ao conectar com MediocreToons (HTTP {e.code}).")
        except Exception as e:
            logger.error(f"[{self.name}] Falha no login Exception: {e}")
            raise Exception(f"Erro inesperado ao conectar com MediocreToons: {e}")

    def has_active_login(self):
        return self.token is not None

    def _fetch_api(self, url):
        if not self.has_active_login():
            raise Exception("A MediocreToons requer login obrigatório. Faça login no aplicativo primeiro.")
            
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8', errors='ignore')
            return json.loads(data)

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")
        
        if not self.has_active_login():
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("mediocre_email")
                password = settings.load("mediocre_password")
                
                if not email or not password:
                    raise Exception("Credenciais não configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso' .")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")
        
        parts = [p for p in series_url.split('?')[0].split('/') if p]
        
        try:
            obra_id = None
            if 'obra' in parts:
                obra_id = parts[parts.index('obra') + 1]
            elif 'obras' in parts:
                obra_id = parts[parts.index('obras') + 1]
            else:
                nums = [p for p in parts if p.isdigit()]
                if nums:
                    obra_id = nums[0]
                else:
                    raise Exception("URL inválida ou ID da obra não encontrado.")
            
            details_url = f"{self.api_url}/obras/{obra_id}"
            details_data = self._fetch_api(details_url)
            
            chapters_data = details_data.get('capitulos', [])
            
            if not chapters_data:
                logger.warning(f"[{self.name}] Nenhum capítulo encontrado.")
                return []
                
            all_chapters = []
            for item in chapters_data:
                chap_id = item.get('cap_id')
                chap_num = item.get('cap_num')
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
                    raise Exception("Credenciais não configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso' .")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automático: {e}")
                raise Exception(f"Erro de login: {e}")

        try:
            if '#chapterId=' not in chapter_url:
                raise Exception("Chapter ID ausente na URL")
                
            chapter_id = chapter_url.split('#chapterId=')[1]
            
            api_chap_url = f"{self.api_url}/capitulos/{chapter_id}"
            chap_data = self._fetch_api(api_chap_url)
            
            # Mediocretoons serves chapter pages via a CDN JSON file
            obra_id = chap_data.get('obra', {}).get('id')
            cap_num = chap_data.get('cap_num')
            cap_uuid = chap_data.get('cap_uuid')
            
            if not all([obra_id, cap_num, cap_uuid]):
                raise Exception("Metadados do capítulo incompletos na API.")
                
            cdn_json_url = f"{self.cdn_url}/obras/{obra_id}/capitulos/{cap_num}/{cap_uuid}.json"
            
            pages_data = self._fetch_api(cdn_json_url)
            if not pages_data:
                raise Exception("O capítulo não possui imagens acessíveis")
                
            images = []
            for p in pages_data:
                img_url = p.get('url') or p.get('src')
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


