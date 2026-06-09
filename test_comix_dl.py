import sys
import os
import json
import urllib.request
sys.path.append(os.path.abspath('.'))

from core.scrapers.comix_scraper import ComixScraper

def test_download():
    scraper = ComixScraper()
    # Pega um mangá que sabemos que tem imagens pra testar o scraper real
    print("Obtendo capítulos...")
    try:
        groups = scraper.get_chapter_groups("https://comix.to/comic/solo-leveling")
        all_chaps = []
        for v in groups.values():
            all_chaps.extend(v)
            
        if not all_chaps:
            print("Nenhum capítulo encontrado!")
            return
            
        chap_url = all_chaps[0]
        print("Obtendo imagens do capítulo:", chap_url)
        images = scraper.get_chapter_images(chap_url)
        if not images:
            print("Nenhuma imagem encontrada!")
            return
            
        print(f"Encontradas {len(images)} imagens. Testando download da primeira imagem encriptada ou normal...")
        # Acha uma imagem com #scrambled pra testar, se não tiver testa a primeira
        img_url = next((img for img in images if "#scrambled" in img), images[0])
        print("Baixando:", img_url)
        
        output_path = "test_img.jpg"
        scraper.download_image(img_url, output_path)
        
        # Verificar o tipo de arquivo pra ver se baixou HTML do cloudflare
        with open(output_path, "rb") as f:
            header = f.read(10)
            print("Primeiros 10 bytes do arquivo baixado:", header.hex())
            if b"<!DOCTYPE" in header or b"<html" in header:
                print("ERRO: Baixou página HTML em vez de imagem. (Cloudflare bloqueando ou erro 403)")
            else:
                print("Arquivo salvo com sucesso, e os bytes parecem corretos.")
    except Exception as e:
        print("Erro durante o teste:", e)

if __name__ == "__main__":
    test_download()
