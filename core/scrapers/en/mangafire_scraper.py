import base64
import urllib.parse
from core.scrapers.base_scraper import BaseScraper
from core.utils.uc_manager import get_cf_session

class VrfSigner:
    TABLE_1 = "yINlmUNho8VYJT+ibTIP+9ESiULpVEtMOoD6U6lRE0R/xwXo/Xp9NrUgC4cw/Lmo33vUyjUE40kUoEWIr/fxfNNcq2s79ShQ5NhNrFnJ4hXPwOu/SuXzIbuTQKGFvfm08E9jvCfqAtoDqvQq3dVWPQFmJjgvkISBeXY3BgANR+yVnjGbcxZ47d6kLNfZPIayTq3/YGySb1KuVZodWp/WGNAO5pfMcpaK53Hhs0allBszaMaxuouOwdxbwgxIw6YunSsXjI05Yi0j9j4eHKfSXR8Ifo/Od+8iamRfCXTyvm7NGRGYdcQ0ywcK/u6RXhrbcCm4t2eCtrDgQVecJGkQ+A=="
    KEY_1 = "0Ec58JOY3uBzJK9m3zqIOpdlF7UFiax9DmA="
    
    TABLE_2 = "IUFltCxD3Oc2cwCgkJffthaOg9cgPUb0LgW6H/VtfcF0kc5F25t+aWj6JH9VOhOaY0rAFdUxlDnl5BLNvwEJvQtP5qcw7vdb/K+chnbwnspSHT8mz5lqwz41TezG0hkO06FTjJZhsyNuFLDpD2ZZxQj/QIRcF90zpmQ7Byu483WsQqUE0C342HL+JXngRB6fRzxRyVTaKu83h7UYTJ0QMt6ixFh6S3F8gqkKwrGTL3jHNBsD45UnifK8+RGtishQV2K3rujLKEkiZxpr2dYcudFW4oFsDKhad3CLBvuyTqsCo4B7mL5IKQ1vXo/MOOvq1I1d8ar9X6Ttu5KF4fZgiA=="
    KEY_2 = "AAdjb1iPY8CiDmq9H34tKTBF8a3oDQ=="
    
    TABLE_3 = "NQHlu1/wVO5EmkwQymF810qqY2xG1k2obcas4Z9mCsPEIFl9pRIjFxbJ7ybMHbBckT5Ton85E0FOeHezbh/mjlEYpmpnlXOS8dgrqeq2KfxImTh1YK9y0PeMNhzA1OQzSY9brYOJq/l2QnE/hwOeZIhPixVSKIUlDb5vLcH6RWKxkIEMuP0bDwIqQ71AJJaEaMJL7A6YtyIwoRT+L5v4aZzodN/0+3nOGsfblFjgxSfPzVDjNFeNl5P26+kEC/8AHgdrpAbt3hHz3HrRN1Y6e+JHgF7ncFWnoF0y3THL1S71WgWGCa6KtSzTCCG58n68nTyj2T3Sshk7utqCtMi/ZQ=="
    KEY_3 = "DELOJgPsVaCcblDtTGMdHzM="
    
    STAGES = [
        (base64.b64decode(TABLE_1), base64.b64decode(KEY_1), 0x5A),
        (base64.b64decode(TABLE_2), base64.b64decode(KEY_2), 0x35),
        (base64.b64decode(TABLE_3), base64.b64decode(KEY_3), 0xBA)
    ]

    def _encrypt_stage(self, data: bytes, table: bytes, key: bytes, iv: int) -> bytes:
        out = bytearray(len(data))
        prev = iv
        key_size = len(key)
        for i in range(len(data)):
            prev = table[(data[i] ^ key[i % key_size] ^ prev) & 0xFF] & 0xFF
            out[i] = prev
        return bytes(out)

    def sign(self, path: str) -> str:
        data = path.encode('utf-8')
        for table, key, iv in self.STAGES:
            data = self._encrypt_stage(data, table, key, iv)
        return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

    def sign_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path.startswith('/api'):
            return url
            
        path_for_sign = path[4:] # remove /api
            
        qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        # sort by key
        qs.sort(key=lambda x: x[0])
        
        if qs:
            qs_parts = []
            last_key = ""
            index = 0
            for key, val in qs:
                new_key = key
                if key.endswith("[]"):
                    if last_key != key:
                        index = 0
                    last_key = key
                    new_key = key[:-2] + f"[{index}]"
                    index += 1
                
                # We need to URL encode the value just like the Kotlin okhttp URL builder would?
                # Actually, in Kotlin buildString: "$newKey=$value" where value is the decoded value or encoded?
                # queryParameterValues returns DECODED values!
                # So we must use decoded values in the signature string.
                # In parse_qsl, values are already unquoted (decoded).
                qs_parts.append(f"{new_key}={val}")
            
            path_for_sign += "?" + "&".join(qs_parts)
            
        vrf = self.sign(path_for_sign)
        
        # Build new query with sorted params + vrf
        qs.append(('vrf', vrf))
        new_query = urllib.parse.urlencode(qs)
        new_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        return new_url

class MangaFireScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://mangafire.to"
        self.signer = VrfSigner()

    def _get_hid(self, url: str) -> str:
        # Example url: https://mangafire.to/manga/solo-leveling.rxzvl
        # We need the last part, and then what is after the dot.
        last_part = url.rstrip('/').split('/')[-1]
        if '.' in last_part:
            return last_part.split('.')[-1]
        if '-' in last_part:
            return last_part.split('-')[0]
        return last_part

    def get_chapters(self, series_url):
        print(f"MangaFire: Analisando url da série {series_url}...")
        self.base_url = f"https://{urllib.parse.urlparse(series_url).netloc}"
        session = get_cf_session(self.base_url)
        session.headers.update({
            'Accept': 'application/json'
        })
        
        hid = self._get_hid(series_url)
        
        chapters = []
        page = 1
        
        # MangaFire loads chapters via /api/titles/{hid}/chapters
        while True:
            # According to Kotlin source: language=en, sort=number, order=desc, page=page, limit=200
            api_url = f"{self.base_url}/api/titles/{hid}/chapters?language=en&limit=200&order=desc&page={page}&sort=number"
            signed_url = self.signer.sign_url(api_url)
            
            res = session.get(signed_url)
            if res.status_code != 200:
                print(f"Falha ao obter capítulos na página {page}: {res.status_code}")
                break
                
            data = res.json()
            items = data.get('items', [])
            
            if not items:
                break
                
            for item in items:
                # Build chapter URL from the series_url and chapter data
                # Actually, the base class requires URL strings.
                # However, MangaFire's chapter URLs usually look like series_url/chapter-xxx
                # Or we can just store the chapter ID as the URL for our own internal use.
                # In Kotlin: chapter_number, volume_number. But for getPageList it uses the ID!
                # We'll just encode the ID into a fake URL or append it so we can extract it in get_chapter_images
                # Example item: {'id': 12345, ...}
                chap_id = item.get('id')
                # we pass fake URL to get_chapter_images
                if chap_id:
                    fake_chap_url = f"{self.base_url}/api/chapters/{chap_id}"
                    chapters.append(fake_chap_url)
            
            # Check meta for pagination
            meta = data.get('meta', {})
            last_page = meta.get('lastPage', 1)
            
            if page >= last_page:
                break
                
            page += 1

        return chapters # Already sorted desc

    def get_chapter_images(self, chapter_url):
        # chapter_url will be f"{self.base_url}/api/chapters/{chap_id}"
        print(f"MangaFire: Buscando imagens para {chapter_url}...")
        session = get_cf_session(self.base_url)
        session.headers.update({
            'Accept': 'application/json'
        })
        
        signed_url = self.signer.sign_url(chapter_url)
        res = session.get(signed_url)
        
        if res.status_code != 200:
            raise Exception(f"Falha ao obter imagens do capítulo: {res.status_code}")
            
        data = res.json()
        
        # response has data -> pages -> [] -> url
        # Kotlin: data.data.pages.map { it.url }
        images = []
        pages = data.get('data', {}).get('pages', [])
        for page in pages:
            img_url = page.get('url')
            if img_url:
                images.append(img_url)
                
        return images
