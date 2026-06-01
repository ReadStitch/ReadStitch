import logging
import urllib.request
import json
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class VerdinhaScraper(BaseScraper):
    """Scraper para o site Verdinha (requer login)."""
    
    @property
    def name(self):
        return "Verdinha"

    def __init__(self):
        super().__init__()
        self.base_url = "https://verdinha.wtf"
        self.api_url = "https://api.verdinha.wtf"
        self.cdn_url = "https://api.verdinha.wtf/cdn"
        self.headers.update({
            'Accept': 'application/json',
            'Referer': f"{self.base_url}/",
            'Origin': self.base_url,
            'scan-id': '1'
        })
        self.token = None

    def login(self, email, password):
        """Autentica na API da Verdinha e salva o token."""
        logger.info(f"[{self.name}] Tentando login com {email}")
        try:
            url = f"{self.api_url}/auth/login"
            payload = {
                "login": email.strip(),
                "senha": password,
                "tipo_usuario": "usuario"
            }
            data = json.dumps(payload).encode('utf-8')
            
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                
                # Suporta nomes variados como access_token ou token
                token = resp_data.get('access_token') or resp_data.get('token')
                
                if not token:
                    raise Exception("Token nÃ£o retornado pela API")
                    
                self.token = token
                self.headers['Authorization'] = f"Bearer {token}"
                
                logger.info(f"[{self.name}] Login efetuado com sucesso!")
                return True
        except Exception as e:
            logger.error(f"[{self.name}] Falha no login: {e}")
            if "401" in str(e):
                raise Exception("Falha de autenticaÃ§Ã£o: E-mail ou Senha invÃ¡lidos.")
            raise Exception("Falha de autenticaÃ§Ã£o. Verifique suas credenciais.")

    def has_active_login(self):
        return self.token is not None

    def _fetch_api(self, url):
        if not self.has_active_login():
            raise Exception("A Verdinha requer login obrigatÃ³rio. FaÃ§a login no aplicativo primeiro.")
            
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
                email = settings.load("verdinha_email")
                password = settings.load("verdinha_password")
                
                if not email or not password:
                    raise Exception("Credenciais nÃ£o configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso' .")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automÃ¡tico: {e}")
                raise Exception(f"Erro de login: {e}")
        
        # Extrai o ID da URL da sÃ©rie
        # Ex: https://verdinha.wtf/obra/10946/alguma-coisa
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
                    raise Exception("URL invÃ¡lida ou ID da obra nÃ£o encontrado.")
            
            details_url = f"{self.api_url}/obras/{obra_id}"
            details_data = self._fetch_api(details_url)
            
            chapters_data = details_data.get('capitulos', [])
            
            if not chapters_data:
                logger.warning(f"[{self.name}] Nenhum capÃ­tulo encontrado (tem certeza que tem acesso VIP ou o mangÃ¡ possui caps?)")
                return []
                
            all_chapters = []
            for item in chapters_data:
                chap_id = item.get('cap_id')
                chap_num = item.get('cap_numero')
                
                if chap_id and chap_num is not None:
                    # Usamos a URL fake com o chap_num para o gui ler bonito e passamos o ID no fragmento
                    url = f"{self.base_url}/capitulo-{chap_num}#chapterId={chap_id}"
                    all_chapters.append(url)
                    
            logger.info(f"[{self.name}] Encontrados {len(all_chapters)} capÃ­tulos")
            return all_chapters
            
        except Exception as e:
            logger.error(f"[{self.name}] Erro ao obter capÃ­tulos: {e}")
            raise Exception(f"Falha ao obter a lista de capÃ­tulos: {e}")

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        if not self.has_active_login():
            try:
                from core.services.settings_handler import SettingsHandler
                settings = SettingsHandler()
                email = settings.load("verdinha_email")
                password = settings.load("verdinha_password")
                
                if not email or not password:
                    raise Exception("Credenciais nÃ£o configuradas. Preencha o E-mail e Senha no painel 'Credenciais de Acesso'.")
                    
                self.login(email, password)
            except Exception as e:
                logger.error(f"[{self.name}] Erro ao tentar login automÃ¡tico: {e}")
                raise Exception(f"Erro de login: {e}")

        try:
            if '#chapterId=' not in chapter_url:
                raise Exception("Chapter ID ausente na URL")
                
            chapter_id = chapter_url.split('#chapterId=')[1]
            
            api_chap_url = f"{self.api_url}/capitulos/{chapter_id}"
            chap_data = self._fetch_api(api_chap_url)
            
            pages = chap_data.get('cap_paginas', [])
            if not pages:
                raise Exception("O capÃ­tulo nÃ£o possui imagens acessÃ­veis")
                
            images = []
            for p in pages:
                img_path = p.get('path')
                if img_path:
                    images.append(f"{self.cdn_url}/{img_path.lstrip('/')}")
                    
            logger.info(f"[{self.name}] Encontradas {len(images)} imagens")
            return images
            
        except Exception as e:
            logger.error(f"[{self.name}] Falha ao obter imagens: {e}")
            raise Exception(f"Falha ao obter imagens do capÃ­tulo: {e}")


