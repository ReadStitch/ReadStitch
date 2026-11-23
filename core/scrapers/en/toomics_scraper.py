import os
import re
import time
import logging
from typing import List, Dict, Optional
from ..base_scraper import BaseScraper
from core.utils.uc_manager import get_uc_driver

logger = logging.getLogger(__name__)

class ToomicsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://toomics.com"
        self.headers['Referer'] = 'https://toomics.com/'
        self.credentials = None
        self.series_title = ""
        self.preferred_group = "Gratuitos"
        self._logged_in = False

    @property
    def name(self) -> str:
        return "Toomics"

    def _extract_lang(self, url: str) -> str:
        m = re.search(r'toomics\.com/([a-z]{2}(?:-[a-z]{2})?)/', url, re.IGNORECASE)
        return m.group(1) if m else "en"

    def _handle_age_verification(self, driver, target_url: str):
        try:
            if 'age_verification' in driver.current_url.lower():
                logger.info(f"[{self.name}] Tela de verificação de idade detectada. Aplicando bypass...")
                driver.execute_script(f"if (typeof Base !== 'undefined' && Base.setDisplay) {{ Base.setDisplay('A', '{target_url}'); }}")
                time.sleep(2)
        except Exception as e:
            logger.warning(f"[{self.name}] Erro ao tentar bypass de verificação de idade: {e}")

    def _login_if_needed(self, driver, lang: str = "en"):
        if not self.credentials or self._logged_in:
            return

        email, password = self.credentials
        if not email or not password:
            return

        try:
            login_url = f"{self.base_url}/{lang}/index/login"
            logger.info(f"[{self.name}] Tentando realizar login em {login_url}...")
            driver.get(login_url)
            time.sleep(2)
            self._handle_age_verification(driver, login_url)

            # Preencher campos de login
            driver.execute_script('''
                const emailInput = document.querySelector('#user_id, input[name="user_id"]');
                const passInput = document.querySelector('#user_pw, input[name="user_pw"]');
                if (emailInput && passInput) {
                    emailInput.value = arguments[0];
                    passInput.value = arguments[1];
                    const form = emailInput.closest('form');
                    if (form) {
                        form.submit();
                    } else {
                        const submitBtn = document.querySelector('button[type="submit"], input[type="submit"], .btn-login');
                        if (submitBtn) submitBtn.click();
                    }
                }
            ''', email, password)
            time.sleep(3)
            self._logged_in = True
            logger.info(f"[{self.name}] Formulário de login submetido.")
        except Exception as e:
            logger.warning(f"[{self.name}] Falha durante o processo de login: {e}")

    def get_chapter_groups(self, series_url: str) -> Dict[str, List[str]]:
        # Caso seja uma URL direta de capítulo/episódio
        if "/webtoon/detail/" in series_url:
            return {"Padrão": [series_url]}

        lang = self._extract_lang(series_url)
        driver = get_uc_driver()

        self._login_if_needed(driver, lang)

        logger.info(f"[{self.name}] Carregando página da série: {series_url}")
        driver.get(series_url)
        time.sleep(2.5)

        self._handle_age_verification(driver, series_url)

        # Captura o título da série
        try:
            page_info = driver.execute_script('''
                const ogTitle = document.querySelector('meta[property="og:title"]')?.getAttribute('content') || '';
                const h1 = document.querySelector('h1, h2.title, .ep-header h2, .ep-header .title')?.innerText || '';
                return { ogTitle: ogTitle, h1: h1, title: document.title };
            ''')
            title = page_info.get('ogTitle') or page_info.get('h1') or page_info.get('title') or ''
            title = title.replace('Toomics -', '').replace('- Toomics', '').strip()
            if title:
                self.series_title = title
                logger.info(f"[{self.name}] Título identificado: {self.series_title}")
        except Exception as e:
            logger.debug(f"[{self.name}] Não foi possível obter título: {e}")

        # Extração dos episódios
        raw_episodes = driver.execute_script('''
            const items = Array.from(document.querySelectorAll('ol.list-ep li'));
            return items.map(li => {
                const link = li.querySelector('a.js-episode-link') || li.querySelector('a');
                const num = li.querySelector('.cell-num')?.innerText?.trim() || '';
                const onclick = link ? (link.getAttribute('onclick') || '') : '';
                const href = link ? (link.getAttribute('href') || '') : '';
                const isLock = !!li.querySelector('.lock, .sp-lock, .coin-type5, em.cointype05') || onclick.includes('popupForStat');
                return {
                    num: num,
                    isLock: isLock,
                    onclick: onclick,
                    href: href
                };
            });
        ''')

        if not raw_episodes:
            raise Exception("Nenhum episódio encontrado na página do Toomics.")

        all_chapters = []
        free_chapters = []

        for ep in raw_episodes:
            onclick = ep.get('onclick', '')
            href = ep.get('href', '')
            ep_path = None

            # Extrai o caminho relativo ou absoluto para o detalhe
            match = re.search(r"(['\"])(/[^'\"]*webtoon/detail/[^'\"]+)\1", onclick)
            if match:
                ep_path = match.group(2)
            elif href and '/webtoon/detail/' in href:
                ep_path = href

            if ep_path:
                full_url = f"{self.base_url}{ep_path}" if ep_path.startswith('/') else ep_path
                all_chapters.append(full_url)
                if not ep.get('isLock', False):
                    free_chapters.append(full_url)

        def extract_num(url_str):
            m = re.search(r'/ep/(\d+(?:\.\d+)?)/', url_str)
            return float(m.group(1)) if m else 999999.0

        all_chapters.sort(key=extract_num)
        free_chapters.sort(key=extract_num)

        # Se houver capítulos bloqueados e o usuário não tiver autenticado
        if free_chapters and len(free_chapters) < len(all_chapters):
            if self._logged_in:
                self.preferred_group = "Todos"
                return {
                    "Todos": all_chapters,
                    "Gratuitos": free_chapters
                }
            else:
                self.preferred_group = "Gratuitos"
                return {
                    "Gratuitos": free_chapters,
                    "Todos (VIP)": all_chapters
                }

        self.preferred_group = "Padrão"
        return {"Padrão": all_chapters}

    def get_chapters(self, series_url: str) -> List[str]:
        groups = self.get_chapter_groups(series_url)
        if self.preferred_group in groups:
            return groups[self.preferred_group]
        first_key = list(groups.keys())[0]
        return groups[first_key]

    def get_chapter_images(self, chapter_url: str) -> List[str]:
        lang = self._extract_lang(chapter_url)
        driver = get_uc_driver()

        self._login_if_needed(driver, lang)

        logger.info(f"[{self.name}] Carregando capítulo: {chapter_url}")
        driver.get(chapter_url)
        time.sleep(2.5)

        self._handle_age_verification(driver, chapter_url)

        # Verificar se redirecionou para tela de login ou popup de registro
        current_url = driver.current_url.lower()
        if 'popup_type/register' in current_url or '/index/login' in current_url:
            raise Exception("Capítulo VIP bloqueado. É necessário estar logado com uma conta VIP do Toomics para acessar.")

        # Extrair links de imagens
        imgs = driver.execute_script('''
            const selectors = '#viewer-img img, #viewer img, .viewer-img img, .viewer-body img, .viewer img, #contents img';
            const elements = Array.from(document.querySelectorAll(selectors));
            return elements.map(img => {
                return img.getAttribute('data-src') || img.getAttribute('data-original') || (!img.src.startsWith('data:') ? img.src : null);
            }).filter(Boolean);
        ''')

        filtered = []
        for img in imgs:
            if not isinstance(img, str) or not img.startswith('http'):
                continue
            img_lower = img.lower()
            # Ignora ícones, banners e miniaturas
            if any(ign in img_lower for ign in ['logo', 'banner', 'icon', 'arrow', 'btn', 'thumb']):
                continue
            if 'toon-g' in img_lower or 'toomics' in img_lower:
                filtered.append(img)

        if not filtered:
            # Fallback para qualquer imagem encontrada nos selectors se o filtro foi rigoroso demais
            filtered = [i for i in imgs if isinstance(i, str) and i.startswith('http')]

        if not filtered:
            raise Exception("Nenhuma imagem encontrada no capítulo do Toomics.")

        logger.info(f"[{self.name}] {len(filtered)} imagens encontradas.")
        return filtered
