import os
import urllib.request
import urllib.parse
import json
import re
import concurrent.futures
from ..base_scraper import BaseScraper

class ComicWalkerScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api_viewer_url = "https://comic-walker.com/api/contents/viewer?episodeId={}&imageSizeType=width%3A1284"

    def get_chapters(self, series_url):
        req = urllib.request.Request(series_url, headers=self.headers)
        try:
            html = urllib.request.urlopen(req).read().decode('utf-8')
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao acessar {series_url}: {e}")
            return {}

        match = re.search(r'<script id="__NEXT_DATA__".*?>(.*?)</script>', html)
        if not match:
            return {}
        
        data = json.loads(match.group(1))
        page_props = data.get('props', {}).get('pageProps', {})
        queries = page_props.get('dehydratedState', {}).get('queries', [])
        chapters = []

        # If it's an episode URL, fetch just the single episode
        if '/episodes/' in series_url:
            for q in queries:
                if 'episode' in str(q.get('queryKey', [])):
                    ep_data = q.get('state', {}).get('data', {}).get('episode')
                    if ep_data:
                        title = ep_data.get('title', 'Episode')
                        if ep_data.get('subTitle'):
                            title += " - " + ep_data['subTitle']
                        
                        num_match = re.search(r'(\d+(?:\.\d+)?)', title)
                        if num_match:
                            chapter_num = num_match.group(1)
                            url = self.api_viewer_url.format(ep_data['id']) + f"&chapter={chapter_num}"
                        else:
                            url = self.api_viewer_url.format(ep_data['id']) + f"&cap=0"
                        chapters.append(url)
                        return chapters

        # If it's a series URL, fetch all free available episodes
        for q in queries:
            if 'workCode' in str(q.get('queryKey', [])) and 'state' in q:
                work = q['state'].get('data', {})
                for k in ['latestEpisodes', 'firstEpisodes']:
                    episodes_group = work.get(k)
                    if isinstance(episodes_group, dict) and 'result' in episodes_group:
                        for ep in episodes_group['result']:
                            title = ep.get('title', 'Episode')
                            if ep.get('subTitle'):
                                title += " - " + ep['subTitle']
                                
                            num_match = re.search(r'(\d+(?:\.\d+)?)', title)
                            if num_match:
                                chapter_num = num_match.group(1)
                                url = self.api_viewer_url.format(ep['id']) + f"&chapter={chapter_num}"
                            else:
                                url = self.api_viewer_url.format(ep['id']) + f"&cap=0"
                            chapters.append(url)
        
        return chapters

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)
        
        req = urllib.request.Request(chapter_url, headers=self.headers)
        try:
            viewer_json = urllib.request.urlopen(req).read().decode('utf-8')
            viewer_data = json.loads(viewer_json)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao obter informações do visualizador para {chapter_url}: {e}")
            return 0
            
        manuscripts = viewer_data.get('manuscripts', [])
        if not manuscripts:
            return 0

        def _download_and_decrypt(args):
            idx, page_info = args
            img_url = page_info.get('drmImageUrl')
            drm_hash = page_info.get('drmHash')
            
            if not img_url or not drm_hash:
                return None
                
            req_img = urllib.request.Request(img_url, headers=self.headers)
            try:
                with urllib.request.urlopen(req_img) as response:
                    data = response.read()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro ao baixar {img_url}: {e}")
                return None
                
            # Decrypt XOR
            key = bytes.fromhex(drm_hash)
            decrypted = bytearray()
            for i, b in enumerate(data):
                decrypted.append(b ^ key[i % len(key)])
            
            decrypted_data = bytes(decrypted)
                
            # Verify magic bytes and get extension
            ext = 'jpg'
            if decrypted_data.startswith(b'\x89PNG\r\n\x1a\n'):
                ext = 'png'
            elif decrypted_data.startswith(b'\xff\xd8\xff'):
                ext = 'jpg'
            elif decrypted_data.startswith(b'RIFF') and decrypted_data[8:12] == b'WEBP':
                ext = 'webp'
                
            filename = f"{idx+1:03d}.{ext}"
            filepath = os.path.join(target_dir, filename)
            
            if not (os.path.exists(filepath) and os.path.getsize(filepath) == len(decrypted_data)):
                with open(filepath, 'wb') as f:
                    f.write(decrypted_data)
                    
            return filepath

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_download_and_decrypt, enumerate(manuscripts)))
            
        return len(manuscripts)
