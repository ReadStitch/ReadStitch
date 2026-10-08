import os
import time
import re
import logging
from ..base_scraper import BaseScraper
from core.utils.uc_manager import get_uc_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

class KakaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        
    def get_chapter_groups(self, series_url, progress_callback=None):
        return {"Padrão": self.get_chapters(series_url, progress_callback=progress_callback)}
        
    def _get_credentials(self):
        """Carrega email e senha das configurações ou usa os valores padrão."""
        try:
            from core.services.settings_handler import SettingsHandler
            settings = SettingsHandler()
            email = settings.load("kakao_email") or ""
            password = settings.load("kakao_password") or ""
        except:
            email = ""
            password = ""
        if not email and hasattr(self, 'credentials') and self.credentials:
            email, password = self.credentials
        return email, password

    def _fill_login_form(self, driver):
        """Preenche e submete o formulário de login do Kakao usando Selenium."""
        email, password = self._get_credentials()
        if not email or not password:
            logger.warning("Credenciais do KakaoPage não configuradas.")
            return False
            
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "loginId")))
        except TimeoutException:
            return False
            
        try:
            driver.set_window_position(0, 0)
            driver.maximize_window()
        except:
            pass
            
        try:
            driver.find_element(By.NAME, "loginId").send_keys(email)
            driver.find_element(By.NAME, "password").send_keys(password)
            
            try:
                ssi = driver.find_elements(By.CSS_SELECTOR, "input#staySignedIn")
                if ssi:
                    driver.execute_script("arguments[0].click();", ssi[0])
            except:
                pass
                
            driver.find_element(By.CSS_SELECTOR, "button.btn_g.highlight.submit").click()
            
            # Wait for login to complete (URL changes from accounts.kakao.com or captcha is solved)
            start_wait = time.time()
            while time.time() - start_wait < 60:
                if "accounts.kakao.com" not in driver.current_url:
                    break
                time.sleep(1)
                
            return True
        except Exception as e:
            logger.error(f"Erro ao preencher form: {e}")
            return False

    def _do_login(self, driver, progress_callback=None):
        try:
            if progress_callback: progress_callback("Verificando autenticação no KakaoPage...")
            driver.get("https://page.kakao.com/main")
            time.sleep(2)
            
            # Verifica se já está logado (botão '캐시' existe)
            if driver.find_elements(By.XPATH, "//button[contains(., '캐시')]") or not driver.find_elements(By.XPATH, "//button[contains(., '로그인')]"):
                if progress_callback: progress_callback("Já está autenticado!")
                return True
                
            login_btns = driver.find_elements(By.XPATH, "//button[contains(., '로그인')]")
            if login_btns:
                login_btns[0].click()
                time.sleep(3)
                self._fill_login_form(driver)
                
                if driver.find_elements(By.XPATH, "//button[contains(., '캐시')]") or not driver.find_elements(By.XPATH, "//button[contains(., '로그인')]"):
                    if progress_callback: progress_callback("Login efetuado com sucesso!")
                    return True
                else:
                    if progress_callback: progress_callback("Falha no login (possível CAPTCHA ou credencial incorreta).")
                    return False
            else:
                return True
        except Exception as e:
            logger.error(f"Erro no login Kakao: {e}")
            return False

    def get_chapters(self, series_url, progress_callback=None):
        if not series_url.startswith('http'):
            series_url = 'https://' + series_url
            
        if "viewer=" in series_url or "/viewer/" in series_url:
            return [series_url]
            
        chapters = []
        profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "kakao_profile_uc"))
        
        driver = get_uc_driver(profile_dir=profile_dir, extra_args=["--disable-web-security", "--disable-blink-features=AutomationControlled"])
        
        # Tenta login
        self._do_login(driver, progress_callback)
        
        if progress_callback: progress_callback("Acessando a página da obra...")
        try:
            driver.get(series_url)
            time.sleep(3)
        except:
            pass
            
        max_clicks = 60
        clicks = 0
        empty_reads = 0
        last_chaps_count = 0
        stuck_count = 0
        
        while clicks < max_clicks:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            
            curr_chaps = driver.execute_script("return document.querySelectorAll('li.list-child-item').length")
            if progress_callback:
                progress_callback(f"Rolando a página... {curr_chaps} capítulos encontrados (Clique {clicks}/{max_clicks})")
                
            if curr_chaps == last_chaps_count:
                stuck_count += 1
                if stuck_count >= 5:
                    break
            else:
                stuck_count = 0
                last_chaps_count = curr_chaps
            
            btns = driver.find_elements(By.CSS_SELECTOR, "img[alt='아래 화살표']")
            if btns:
                empty_reads = 0
                try:
                    parent = driver.execute_script("return arguments[0].parentElement;", btns[0])
                    if parent:
                        driver.execute_script("arguments[0].click();", parent)
                        time.sleep(0.5)
                        clicks += 1
                        continue
                except:
                    pass
            else:
                empty_reads += 1
                if empty_reads >= 5:
                    break
                time.sleep(1)
                continue
                
            break
            
        if progress_callback: progress_callback("Extraindo links dos capítulos carregados...")
            
        links = driver.execute_script("""
            let items = document.querySelectorAll("li.list-child-item");
            return Array.from(items).map(li => {
                let text = li.innerText.replace(/\\n/g, ' ');
                let a = li.querySelector("a[href*='/viewer/']");
                let url = a ? a.href : '';
                return {text: text, url: url};
            }).filter(x => x.url !== '');
        """)
        
        for item in links:
            url = item['url']
            if not url.startswith('http'):
                url = f"https://page.kakao.com{url}"
                
            text = item['text']
            num_match = re.search(r'(\d+(?:\.\d+)?)\s*화', text)
            if not num_match:
                num_match = re.search(r'(\d+(?:\.\d+)?)', text)
                
            if num_match:
                if '?' in url:
                    url = f"{url}&chapter={num_match.group(1)}"
                else:
                    url = f"{url}?chapter={num_match.group(1)}"
            
            base_url = url.split('?chapter=')[0].split('&chapter=')[0]
            if not any(base_url in existing_url for existing_url in chapters):
                chapters.append(url)
                
        if not chapters:
            raise Exception("Não foi possível carregar a lista de capítulos. Verifique se a URL está correta ou forneça o link direto do visualizador.")
            
        chapters.reverse()
        return chapters

    def get_chapter_images(self, chapter_url):
        images = []
        profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "kakao_profile_uc"))
        
        driver = get_uc_driver(profile_dir=profile_dir, extra_args=["--disable-web-security", "--disable-blink-features=AutomationControlled"])
        
        try:
            driver.get(chapter_url)
            time.sleep(4)
        except:
            pass
            
        # ── Step 1: Handle login-required modal ("로그인 하기") ─────────────
        try:
            login_modal_btns = driver.find_elements(By.XPATH, '//div[@role="dialog"]//button[contains(., "로그인 하기")]')
            if login_modal_btns:
                logger.info("Login-required modal detected. Navigating to login form...")
                try:
                    driver.set_window_position(0, 0)
                    driver.maximize_window()
                except:
                    pass
                login_modal_btns[0].click()
                time.sleep(3)
                self._fill_login_form(driver)
                driver.get(chapter_url)
                time.sleep(4)
        except Exception as e:
            logger.error(f"Erro ao lidar com modal de login: {e}")

        # ── Step 2: Aguardar carregamento (spinner) ───────────
        try:
            spinners = driver.find_elements(By.CSS_SELECTOR, 'img[alt="로딩중"]')
            if spinners:
                WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'img[alt="로딩중"]')))
        except Exception as e:
            logger.warning(f"Erro ao aguardar carregamento: {e}")
        
        # Verify if there is a region block
        try:
            if driver.find_elements(By.XPATH, '//*[contains(text(), "해당 국가에서는 감상할 수 없는 작품입니다.")]'):
                raise Exception("Acesso bloqueado por região: O KakaoPage bloqueou seu IP. É necessário usar uma VPN sul-coreana.")
        except Exception as e:
            if "VPN" in str(e):
                raise e
                
        # Check if login modal is still there
        try:
            if driver.find_elements(By.XPATH, '//div[@role="dialog"]//button[contains(., "로그인 하기")]'):
                raise Exception("Acesso negado: O capítulo requer login e a autenticação falhou ou as credenciais são inválidas.")
        except Exception as e:
            if "Acesso negado" in str(e):
                raise e
        
        # Now extract images (scroll down to lazy load)
        driver.set_script_timeout(60)
        driver.execute_async_script("""
            var done = arguments[arguments.length - 1];
            let totalHeight = 0;
            let distance = 600;
            let timer = setInterval(() => {
                let scrollHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                window.scrollBy(0, distance);
                totalHeight += distance;
                if(totalHeight >= scrollHeight + window.innerHeight){
                    clearInterval(timer);
                    done();
                }
            }, 150);
        """)
        
        time.sleep(3)
        
        # Extract standard images
        imgs = driver.execute_script("""
            const images = Array.from(document.querySelectorAll('img'));
            return images.map(i => i.src || i.dataset.src).filter(Boolean);
        """)
        for img in imgs:
            if ('download' in img or 'kakaocdn' in img) and 'svg' not in img and 'resize' not in img and 'th3' not in img:
                if img not in images:
                    images.append(img)
                    
        # Extract DRM Canvas images (paid chapters)
        try:
            canvas_b64 = driver.execute_script("""
                return Array.from(document.querySelectorAll('canvas')).map(c => {
                    try { return c.toDataURL("image/jpeg", 0.95); } 
                    catch(e) { return null; }
                }).filter(Boolean);
            """)
            if canvas_b64:
                images.extend(canvas_b64)
        except Exception as e:
            logger.error(f"Erro ao extrair canvas: {e}")
                    
        if not images:
            logger.warning("No images found. Maybe chapter is still locked or canvas is empty.")
            raise Exception("Nenhuma imagem encontrada. O capítulo pode estar bloqueado (pago), requerer captcha, ou a estrutura do site mudou.")
            
        return images
