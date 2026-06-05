from .asura_scraper import AsuraScraper
from .utoon_scraper import UtoonScraper
from .qi_scraper import QiScraper
from .vortex_scraper import VortexScraper
from .comix_scraper import ComixScraper
from .webtoon_scraper import WebtoonScraper
from .kakao_scraper import KakaoScraper
from .piccoma_scraper import PiccomaScraper
from .apecomics_scraper import ApeComicsScraper
from .plumacomics_scraper import PlumaComicsScraper
from .lycantoons_scraper import LycanToonsScraper
from .genz_scraper import GenzScraper
from .naver_scraper import NaverScraper
from .tapas_scraper import TapasScraper
from .roliascan_scraper import RoliascanScraper
from .mangadex_scraper import MangadexScraper
from .astratoons_scraper import AstratoonsScraper

from .geasscomics_scraper import GeassComicsScraper

from .inkapk_scraper import InkapkScraper

from .nexus_scraper import NexusScraper

from .vegitoons_scraper import VegitoonsScraper

from .hipercool_scraper import HipercoolScraper

from .verdinha_scraper import VerdinhaScraper
from .mediocre_scraper import MediocreScraper
from .kagane_scraper import KaganeScraper

def get_scraper_for_url(url):
    url_lower = url.lower()
    if 'webtoons.com' in url_lower:
        return WebtoonScraper()
    elif 'kakao.com' in url_lower:
        return KakaoScraper()
    elif 'utoon.net' in url_lower:
        return UtoonScraper()
    elif 'qimanhwa.com' in url_lower:
        return QiScraper()
    elif 'vortexscans.org' in url_lower or 'hivetoons.org' in url_lower:
        return VortexScraper()
    elif 'comix.to' in url_lower or 'comick' in url_lower:
        return ComixScraper()
    elif 'piccoma.com' in url_lower:
        return PiccomaScraper()
    elif 'capitoons.com' in url_lower or 'apecomics' in url_lower:
        return ApeComicsScraper()
    elif 'plumacomics' in url_lower:
        return PlumaComicsScraper()
    elif 'lycantoons' in url_lower:
        return LycanToonsScraper()
    elif 'geasscomics' in url_lower:
        return GeassComicsScraper()
    elif 'inkapk' in url_lower:
        return InkapkScraper()
    elif 'tapas.io' in url_lower:
        return TapasScraper()
    elif 'roliascan' in url_lower:
        return RoliascanScraper()
    elif 'mangadex.org' in url_lower or 'mangadex' in url_lower:
        return MangadexScraper()
    elif 'astratoons.com' in url_lower or 'astratoons' in url_lower:
        return AstratoonsScraper()
    elif 'genztoons.org' in url_lower:
        return GenzScraper()
    elif 'comic.naver.com' in url_lower:
        return NaverScraper()
    elif 'nx-toons' in url_lower or 'nexus' in url_lower:
        return NexusScraper()
    elif 'vegitoons' in url_lower:
        return VegitoonsScraper()
    elif 'hiper.cool' in url_lower or 'hipercool' in url_lower:
        return HipercoolScraper()
    elif 'verdinha.wtf' in url_lower or 'verdinha' in url_lower:
        return VerdinhaScraper()
    elif 'mediocrescan.com' in url_lower or 'mediocre' in url_lower:
        return MediocreScraper()
    elif 'kagane.org' in url_lower or 'kagane' in url_lower:
        return KaganeScraper()
    elif 'flamecomics' in url_lower:
        from .flamecomics_scraper import FlameComicsScraper
        return FlameComicsScraper()
    elif 'reset-scans.org' in url_lower or 'resetscans' in url_lower:
        from .resetscans_scraper import ResetScansScraper
        return ResetScansScraper()
    elif 'elftoon.com' in url_lower or 'elftoon' in url_lower:
        from .elftoon_scraper import ElftoonScraper
        return ElftoonScraper()
    # Default to Asura
    return AsuraScraper()
