import os
import urllib.request
import concurrent.futures

class BaseScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def get_chapter_groups(self, series_url):
        # By default, returns a single "Padrão" (Default) group with all chapters
        return {"Padrão": self.get_chapters(series_url)}

    def get_chapters(self, series_url):
        raise NotImplementedError()

    def get_chapter_images(self, chapter_url):
        raise NotImplementedError()

    def download_image(self, url, output_path):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())

    def download_chapter(self, chapter_url, output_dir, chapter_name, max_workers=5):
        target_dir = os.path.join(output_dir, chapter_name)
        os.makedirs(target_dir, exist_ok=True)
        
        images = self.get_chapter_images(chapter_url)
        if not images:
            return 0
            
        def _download(args):
            idx, url = args
            
            # Baixa o conteúdo da imagem
            req = urllib.request.Request(url, headers=self.headers)
            try:
                with urllib.request.urlopen(req) as response:
                    data = response.read()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro ao baixar {url}: {e}")
                return None
                
            if not data:
                return None
                
            # Verifica magic bytes para obter a extensão real
            ext = 'jpg'
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                ext = 'png'
            elif data.startswith(b'\xff\xd8\xff'):
                ext = 'jpg'
            elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
                ext = 'webp'
            elif data[4:8] == b'ftyp' and b'avif' in data[8:12]:
                ext = 'avif'
            elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
                ext = 'gif'
                
            # Converter AVIF/WEBP para PNG para melhor compatibilidade no Windows
            if ext in ('avif', 'webp'):
                try:
                    from PIL import Image
                    import io
                    # Garante que o plugin do avif está carregado
                    if ext == 'avif':
                        import pillow_avif
                        
                    img = Image.open(io.BytesIO(data))
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    data = buf.getvalue()
                    ext = 'png'
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Erro ao converter {ext} para PNG: {e}")
                
            filename = f"{idx+1:03d}.{ext}"
            filepath = os.path.join(target_dir, filename)
            
            # Se já existir, ignora
            if not (os.path.exists(filepath) and os.path.getsize(filepath) == len(data)):
                with open(filepath, 'wb') as f:
                    f.write(data)
                    
            return filepath
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(_download, enumerate(images)))
            
        return len(images)
