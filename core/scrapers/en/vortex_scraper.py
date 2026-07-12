import re
import logging
import requests
import urllib3
from ..base_scraper import BaseScraper

# Suppress SSL warnings for sites with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class VortexScraper(BaseScraper):
    # Known domains that serve this platform
    KNOWN_DOMAINS = [
        "vortexscans.org",
        "vortexscans.com",
        "hivetoons.org",
        "hivetoons.com",
    ]
    # The canonical (current) primary domain
    PRIMARY_DOMAIN = "vortexscans.org"

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "Vortex Scans"

    def _detect_domain(self, url: str) -> str:
        """Return the actual working domain from a given URL, falling back to PRIMARY_DOMAIN."""
        for domain in self.KNOWN_DOMAINS:
            if domain in url:
                return domain
        return self.PRIMARY_DOMAIN

    def _build_url(self, path: str, domain: str) -> str:
        """Build a full URL from a relative path and domain."""
        if path.startswith("http"):
            return path
        return f"https://{domain}{path}"

    def _fetch(self, url: str) -> requests.Response:
        session_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": f"https://{self.PRIMARY_DOMAIN}/",
        }
        resp = requests.get(url, headers=session_headers, timeout=30, verify=False, allow_redirects=True)
        resp.raise_for_status()
        return resp

    def get_chapters(self, series_url: str) -> list:
        if "/chapter" in series_url or "/ch-" in series_url:
            return [series_url]

        domain = self._detect_domain(series_url)

        # If the URL points to a dead domain (hivetoons.com), rewrite it to the primary domain
        if "hivetoons.com" in series_url:
            series_url = series_url.replace("hivetoons.com", self.PRIMARY_DOMAIN)
            domain = self.PRIMARY_DOMAIN

        logger.info(f"[{self.name}] Fetching chapters from: {series_url}")

        resp = self._fetch(series_url)
        html = resp.text

        # The final URL after redirects tells us the real domain
        real_domain = resp.url.split("/")[2]

        slug = [p for p in series_url.strip("/").split("/") if p][-1]

        # 1. Tentar pegar os links que já estão no HTML (a tags)
        pattern = r'href="(/series/' + re.escape(slug) + r'/(?:chapter|ch)-?[0-9\.]+)"'
        links = re.findall(pattern, html)

        if not links:
            # Fallback genérico para a tags
            links = re.findall(r'href="(/series/[^"]+/(?:chapter|ch)-?[0-9\.]+)"', html)
            links = [l for l in links if slug in l]
            
        # 2. Pegar também os dados embutidos (Astro injeta os dados do BD escapados no final do HTML)
        json_slugs = re.findall(r'&quot;slug&quot;:\[\d+,&quot;((?:chapter|ch)-?[0-9\.]+)&quot;\]', html)
        for j_slug in json_slugs:
            links.append(f"/series/{slug}/{j_slug}")

        chapters = set()
        for href in links:
            chapters.add(self._build_url(href, real_domain))

        def get_chap_num(url):
            try:
                match = re.search(r"(?:chapter|ch)-?([0-9\.]+)", url)
                return float(match.group(1)) if match else 0
            except Exception:
                return 0

        result = sorted(list(chapters), key=get_chap_num)
        logger.info(f"[{self.name}] Found {len(result)} chapters.")
        return result

    def get_chapter_images(self, chapter_url: str) -> list:
        logger.info(f"[{self.name}] Fetching images from: {chapter_url}")

        resp = self._fetch(chapter_url)
        html = resp.text

        # Primary method: <meta itemprop="image" content="...">
        images = re.findall(
            r'<meta\s+itemprop=[\'"]image[\'"]\s+content=[\'"](https://[^\'"]+(?:jpg|jpeg|png|webp))[\'"]',
            html,
        )

        if not images:
            # Fallback: any src pointing to a storage subdomain
            images = re.findall(
                r'src=[\'\"](https://storage\.[^\'\"]+(jpg|jpeg|png|webp))[\'\"]',
                html,
            )
            images = [m[0] if isinstance(m, tuple) else m for m in images]

        if not images:
            raise Exception("Nenhuma imagem encontrada no capítulo Vortex.")

        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for img_url in images:
            if img_url not in seen:
                seen.add(img_url)
                ordered.append(img_url)

        logger.info(f"[{self.name}] Found {len(ordered)} images.")
        return ordered
