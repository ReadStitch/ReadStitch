import logging
import json
import re
import os
import concurrent.futures
import requests
import bs4
from ..base_scraper import BaseScraper
from core.utils.uc_manager import get_uc_driver, get_cf_session
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class LycanToonsScraper(BaseScraper):
    """Scraper para LycanToons com resolução visual do DOM."""
    
    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "Lycan Toons"

    def get_chapters(self, series_url):
        logger.info(f"[{self.name}] Fetching chapters for: {series_url}")
        
        slug = series_url.strip('/').split('/')[-1]
        
        # 1. Visitar a página da série para pegar o link do primeiro capítulo
        driver = get_uc_driver()
        session = get_cf_session(series_url)
        time.sleep(3)
        html = driver.page_source
        
        soup = bs4.BeautifulSoup(html, "html.parser")
        first_chap_url = None
        
        # Procura o botão "Começar a ler" (ou qualquer link que aponte para um capítulo da série)
        for a in soup.find_all('a'):
            href = a.get('href', '')
            # O link costuma ser /series/devorador-de-aco/1
            if href.startswith(f"/series/{slug}/") and href != f"/series/{slug}/":
                first_chap_url = f"https://lycantoons.com{href}"
                break
                
        if not first_chap_url:
            # Fallback forçado caso não ache na série
            logger.warning(f"[{self.name}] Não achou botão de começar a ler. Forçando ida para capítulo 1.")
            first_chap_url = f"{series_url}/1"
            
        # 2. Visita a página do capítulo para ler o seletor de capítulos (dropdown <select>)
        logger.info(f"[{self.name}] Acessando página do capítulo para ler a lista: {first_chap_url}")
        session = get_cf_session(first_chap_url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "option")))
        except Exception as e:
            logger.warning(f"[{self.name}] Timeout aguardando opções de capítulo: {e}")
        html = driver.page_source
        soup = bs4.BeautifulSoup(html, "html.parser")
        
        chapters = []
        
        # Procura nas tags <option> do dropdown
        for opt in soup.find_all('option'):
            val = opt.get('value', '')
            if val and str(val).strip():
                # O value geralmente é o slug do capítulo (ex: "1", "capitulo-2")
                chap_link = f"https://lycantoons.com/series/{slug}/{val.strip()}"
                chapters.append(chap_link)
                
        if not chapters:
            # Fallback para tags <a> caso eles mudem de <select> para lista comum
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if href.startswith(f"/series/{slug}/") and href != f"/series/{slug}/":
                    chapters.append(f"https://lycantoons.com{href}")
                    
        # Remove duplicatas
        chapters = list(dict.fromkeys(chapters))
        
        # Ordenar os capítulos numericamente (decrescente)
        def get_num(url):
            m = re.search(r'/([^/]+)$', url)
            if not m: return 0
            val = m.group(1).replace('capitulo-', '')
            try:
                return float(val)
            except:
                return 0
                
        chapters.sort(key=get_num, reverse=True)
        
        if not chapters:
            with open(r"f:\Projetos\programa\ReadStitch\scratch\failed_html_chapters.html", "w", encoding="utf-8") as f:
                f.write(html)
            raise Exception("Não foi possível encontrar a lista de capítulos no DOM")
            
        logger.info(f"[{self.name}] Encontrados {len(chapters)} capítulos!")
        return chapters

    def get_chapter_images(self, chapter_url):
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")
        
        clean_url = chapter_url.split('#')[0]
        driver = get_uc_driver()
        session = get_cf_session(clean_url)
        
        # Aguardar as imagens renderizarem no DOM
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='cdn.lycantoons.com']")))
        except Exception as e:
            logger.warning(f"[{self.name}] Timeout aguardando imagens: {e}")
            
        images = []
        
        # Tentar extrair do React Fiber diretamente para burlar Virtualização e Lazy Loading
        # Isso evita que precisemos fazer scroll na página, o que engatilharia redirecionamentos de anúncios.
        js_script = """
        function searchString(obj, urls, seen) {
            if (!obj || typeof obj !== 'object') return;
            if (seen.has(obj)) return;
            seen.add(obj);
            for (let key in obj) {
                try {
                    let val = obj[key];
                    if (typeof val === 'string' && val.includes('cdn.lycantoons.com')) {
                        let matches = val.match(/https:\\/\\/cdn\\.lycantoons\\.com[^"']+/g);
                        if (matches) { matches.forEach(m => urls.add(m)); }
                        else { urls.add(val); }
                    } else if (typeof val === 'object') {
                        searchString(val, urls, seen);
                    }
                } catch(e) {}
            }
        }
        function findUrlsInFiber(node, urls, seenObj) {
            if (!node) return;
            if (node.memoizedProps) searchString(node.memoizedProps, urls, seenObj);
            findUrlsInFiber(node.child, urls, seenObj);
            findUrlsInFiber(node.sibling, urls, seenObj);
        }
        let rootNode = document.querySelector('#__next') || document.querySelector('body');
        let fiberKey = Object.keys(rootNode).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactContainer$'));
        let urls = new Set();
        let seenObj = new WeakSet();
        if (fiberKey) { findUrlsInFiber(rootNode[fiberKey], urls, seenObj); }
        return Array.from(urls);
        """
        try:
            fiber_urls = driver.execute_script(js_script)
            if fiber_urls:
                for src in fiber_urls:
                    if 'cdn.lycantoons.com' in src:
                        # Em vez de exigir 'page-' ou 'cap-', ignoramos as pastas conhecidas que não são do mangá
                        if not any(x in src.lower() for x in ['/covers/', '/avatars/', '/profile-covers/', '/comments/', '/banners/']):
                            images.append(src)
        except Exception as e:
            logger.warning(f"[{self.name}] Falha ao extrair do React Fiber: {e}")
            
        # Fallback tradicional caso a extração por Fiber falhe (lê do DOM)
        if not images:
            logger.info(f"[{self.name}] Usando fallback de DOM. Realizando scroll...")
            try:
                driver.set_script_timeout(60)
                driver.execute_async_script('''
                    let done = arguments[arguments.length - 1];
                    let lastHeight = 0;
                    let retries = 0;
                    let timer = setInterval(() => {
                        window.scrollBy(0, 800);
                        let currentHeight = document.body.scrollHeight;
                        if (currentHeight === lastHeight) {
                            retries++;
                            if (retries >= 15) { 
                                clearInterval(timer); 
                                done(); 
                            }
                        } else {
                            retries = 0;
                            lastHeight = currentHeight;
                        }
                    }, 100);
                ''')
            except Exception as e:
                logger.warning(f"[{self.name}] Falha no scroll do fallback: {e}")

            html = driver.page_source
            soup = bs4.BeautifulSoup(html, "html.parser")
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and 'http' in src and not any(x in src.lower() for x in ['logo', 'avatar', 'discord', 'banner', 'ui-avatars', '/covers/', '/comments/', '/profile-covers/']):
                    if 'cdn.lycantoons.com' in src:
                        images.append(src)
                    elif 'cdn.discordapp.com' in src:
                        images.append(src)
                        
        # Remover duplicatas e manter ordem
        images = list(dict.fromkeys(images))
        
        if not images:
            raise Exception("O capítulo não possui imagens acessíveis no DOM ou State")
            
        self._uc_cookies = session.cookies.get_dict()
        self._uc_ua = session.headers.get('User-Agent')
            
        logger.info(f"[{self.name}] Encontradas {len(images)} imagens!")
        return images

    def download_image(self, url, output_path):
        headers = self.headers.copy()
        if hasattr(self, '_uc_ua') and self._uc_ua:
            headers['User-Agent'] = self._uc_ua
            
        cookies = {}
        if hasattr(self, '_uc_cookies') and self._uc_cookies:
            cookies = self._uc_cookies
            
        headers['Referer'] = 'https://lycantoons.com/'
        
        res = requests.get(url, headers=headers, cookies=cookies)
        res.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(res.content)

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)
        
        images = self.get_chapter_images(chapter_url)
        if not images:
            return 0
            
        def _download(args):
            idx, url = args
            ext = 'jpg'
            if '.png' in url.lower(): ext = 'png'
            elif '.webp' in url.lower(): ext = 'webp'
            elif '.avif' in url.lower(): ext = 'avif'
            
            filepath = os.path.join(target_dir, f"{idx+1:03d}.{ext}")
            
            if not os.path.exists(filepath):
                try:
                    self.download_image(url, filepath)
                except Exception as e:
                    logger.error(f"Erro ao baixar {url}: {e}")
                    return None
                    
            if ext in ('webp', 'avif'):
                try:
                    from PIL import Image
                    png_path = os.path.join(target_dir, f"{idx+1:03d}.png")
                    if not os.path.exists(png_path):
                        with Image.open(filepath) as img:
                            if img.mode not in ('RGB', 'RGBA'):
                                img = img.convert('RGBA')
                            img.save(png_path, format='PNG')
                        os.remove(filepath)
                        filepath = png_path
                except Exception as e:
                    logger.error(f"Erro ao converter {ext} para PNG: {e}")
                    
            return filepath
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_download, enumerate(images)))
            
        return len(images)
