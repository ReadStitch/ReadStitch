from .en.asura_scraper import AsuraScraper
from .pt_br.tiamanhwa_scraper import TiaManhwaScraper
from .en.utoon_scraper import UtoonScraper
from .en.qi_scraper import QiScraper
from .en.vortex_scraper import VortexScraper
from .en.comix_scraper import ComixScraper
from .en.webtoon_scraper import WebtoonScraper
from .en.genz_scraper import GenzScraper
from .en.tapas_scraper import TapasScraper
from .en.roliascan_scraper import RoliascanScraper
from .en.mangadex_scraper import MangadexScraper
from .en.kagane_scraper import KaganeScraper
from .en.comikey_scraper import ComikeyScraper
from .en.ezmanga_scraper import EzmangaScraper

from .kr.kakao_scraper import KakaoScraper
from .kr.naver_scraper import NaverScraper

from .jp.piccoma_scraper import PiccomaScraper

from .pt_br.apecomics_scraper import ApeComicsScraper
from .pt_br.plumacomics_scraper import PlumaComicsScraper
from .pt_br.lycantoons_scraper import LycanToonsScraper
from .pt_br.geasscomics_scraper import GeassComicsScraper
from .pt_br.inkapk_scraper import InkapkScraper
from .pt_br.astratoons_scraper import AstratoonsScraper
from .pt_br.nexus_scraper import NexusScraper
from .pt_br.vegitoons_scraper import VegitoonsScraper
from .pt_br.hipercool_scraper import HipercoolScraper
from .pt_br.verdinha_scraper import VerdinhaScraper
from .pt_br.blackout_scraper import BlackoutComicsScraper
from .pt_br.mediocre_scraper import MediocreScraper
from .pt_br.empreguetes_scraper import EmpreguetesScraper
from .pt_br.tiraninha_scraper import TiraninhaScraper
from .pt_br.onereader_scraper import OneReaderScraper
from .pt_br.manhastro_scraper import ManhastroScraper
from .pt_br.safirescan_scraper import SafireScanScraper

def get_scraper_for_url(url):
    url_lower = url.lower()
    if 'onereader.net' in url_lower:
        return OneReaderScraper()
    elif 'manhastro.net' in url_lower or 'manhastro' in url_lower:
        return ManhastroScraper()
    elif 'webtoons.com' in url_lower:
        return WebtoonScraper()
    elif 'kakao.com' in url_lower:
        return KakaoScraper()
    elif 'utoon.net' in url_lower:
        return UtoonScraper()
    elif 'qimanhwa.com' in url_lower or 'qimanga.com' in url_lower:
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
    elif 'hiper.cool' in url_lower or 'hipercool' in url_lower or 'lerhentais' in url_lower or 'hipertoon' in url_lower:
        return HipercoolScraper()
    elif 'verdinha.wtf' in url_lower or 'verdinha' in url_lower:
        return VerdinhaScraper()
    elif 'mediocrescan.com' in url_lower or 'mediocre' in url_lower:
        return MediocreScraper()
    elif 'empreguetes.wtf' in url_lower or 'empreguetes' in url_lower:
        return EmpreguetesScraper()
    elif 'kagane.org' in url_lower or 'kagane' in url_lower:
        return KaganeScraper()
    elif 'tiraninha.world' in url_lower or 'tiraninha' in url_lower:
        return TiraninhaScraper()
    elif 'safirescan.site' in url_lower or 'safirescan.xyz' in url_lower or 'safirescan' in url_lower:
        return SafireScanScraper()
    elif 'sushiscan.net' in url_lower or 'sushiscan' in url_lower:
        return SushiScanScraper()
    elif 'tiamanhwa.com' in url_lower or 'tiamanhwa' in url_lower:
        return TiaManhwaScraper()
    elif 'zinmanga.com' in url_lower or 'zinmanga' in url_lower:
        return EzmangaScraper()
    elif 'comikey.com' in url_lower or 'comikey' in url_lower:
        return ComikeyScraper()
    elif 'ezmanga.org' in url_lower or 'ezmanga' in url_lower:
        return EzmangaScraper()
    elif 'flamecomics' in url_lower:
        from .en.flamecomics_scraper import FlameComicsScraper
        return FlameComicsScraper()
    elif 'reset-scans.org' in url_lower or 'resetscans' in url_lower:
        from .en.resetscans_scraper import ResetScansScraper
        return ResetScansScraper()
    elif 'blackoutcomics.com' in url_lower or 'blackoutcomics' in url_lower:
        return BlackoutComicsScraper()
    elif 'elftoon.com' in url_lower or 'elftoon' in url_lower:
        from .en.elftoon_scraper import ElftoonScraper
        return ElftoonScraper()
    elif 'erosect.xyz' in url_lower or 'erosect' in url_lower:
        from .pt_br.erosect_scraper import ErosectScraper
        return ErosectScraper()
    elif 'aniargos.com' in url_lower or 'aniargos' in url_lower:
        from .pt_br.aniargos_scraper import AniArgosScraper
        return AniArgosScraper()
    # Default to Asura
    return AsuraScraper()
