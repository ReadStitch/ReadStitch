import undetected_chromedriver as uc
import time
import requests
import re
import os

class UCManager:
    _instance = None
    _driver = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = UCManager()
        return cls._instance
        
    def __init__(self):
        if UCManager._instance is not None:
            raise Exception("Esta é uma classe Singleton. Use UCManager.get_instance().")
            
    def get_driver(self):
        """Retorna uma instância persistente do driver."""
        if self._driver is None:
            self._init_driver()
        return self._driver
        
    def _init_driver(self, version_override=None):
        options = uc.ChromeOptions()
        # Omitimos o headless=True porque Cloudflare bloqueia headles=new com Turnstile.
        # Movemos a janela para fora da tela para mantê-la invisível sem acionar proteções anti-bot
        options.add_argument('--window-position=-32000,-32000')
        try:
            print("Inicializando undetected_chromedriver...")
            if version_override:
                self._driver = uc.Chrome(options=options, version_main=version_override)
            else:
                self._driver = uc.Chrome(options=options)
        except Exception as e:
            err_msg = str(e)
            print(f"Erro ao inicializar driver: {err_msg}")
            # Tentar auto-recuperar a versão do Chrome
            # Exemplo de erro: "Current browser version is 151.0.7922.138"
            match = re.search(r"Current browser version is (\d+)", err_msg)
            if match and not version_override:
                detected_version = int(match.group(1))
                print(f"Detectada versão local do Chrome: {detected_version}. Tentando novamente...")
                self._init_driver(version_override=detected_version)
            else:
                raise e

    def get_cloudflare_session(self, url: str, wait_timeout: int = 30) -> requests.Session:
        """
        Visita a URL, aguarda a verificação do Cloudflare e retorna uma requests.Session
        configurada com os cookies e User-Agent validados.
        """
        driver = self.get_driver()
        print(f"Acessando URL: {url}...")
        driver.get(url)
        
        # Lógica de espera do Cloudflare (espera sumir 'Just a moment', 'Attention Required', etc)
        start_time = time.time()
        bypassed = False
        while time.time() - start_time < wait_timeout:
            title = driver.title
            if title and not any(cf_txt in title for cf_txt in ["Just a moment", "Cloudflare", "Attention Required", "Um momento", "Verificando"]):
                bypassed = True
                break
            time.sleep(2)
            
        if not bypassed:
            print("AVISO: Timeout aguardando bypass do Cloudflare. A página pode ainda estar bloqueada.")
            
        # Pequena pausa extra para os cookies assentarem
        time.sleep(2)
        
        # Puxa os dados para o requests.Session
        cookies = driver.get_cookies()
        ua = driver.execute_script("return navigator.userAgent")
        
        session = requests.Session()
        for c in cookies:
            session.cookies.set(c['name'], c['value'], domain=c['domain'])
        session.headers.update({
            'User-Agent': ua,
            'Referer': url
        })
        
        return session
        
    def close(self):
        if self._driver:
            try:
                self._driver.quit()
            except:
                pass
            self._driver = None

# Global helper para facilidade
def get_cf_session(url: str) -> requests.Session:
    return UCManager.get_instance().get_cloudflare_session(url)

def get_uc_driver():
    return UCManager.get_instance().get_driver()
