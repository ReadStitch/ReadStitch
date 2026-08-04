<div align="center">
  <a href="https://github.com/ReadStitch/ReadStitch">
    <img alt="ReadStitch Logo" width="180" src="assets/ReadStitchLogo.png">
  </a>

  <h1>ReadStitch</h1>
  <p><strong>A fusão entre SmartStitch e Waifu2x para Webtoons, Manhwas e Manhuas</strong><br/>Baixe raws, una imagens, corte capítulos e melhore a qualidade com upscaling — tudo em um só lugar.</p>

  <p>
    <a href="https://github.com/ReadStitch/ReadStitch/releases/latest"><img src="https://img.shields.io/github/v/release/ReadStitch/ReadStitch?label=release" alt="Latest Release"></a>
    <a href="https://github.com/ReadStitch/ReadStitch/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/ReadStitch/ReadStitch/ci.yml?label=ci" alt="CI"></a>
    <a href="https://github.com/ReadStitch/ReadStitch/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/ReadStitch/ReadStitch/build.yml?label=release" alt="Release Workflow"></a>
    <a href="https://github.com/ReadStitch/ReadStitch/releases"><img src="https://img.shields.io/github/downloads/ReadStitch/ReadStitch/total" alt="Downloads"></a>
    <a href="https://github.com/ReadStitch/ReadStitch/blob/master/LICENSE"><img src="https://img.shields.io/github/license/ReadStitch/ReadStitch" alt="License"></a>
  </p>
</div>

---

## O que é o ReadStitch?

O **ReadStitch** é um projeto construído a partir do repositório **[MedStitch](https://github.com/ViminioSM/MedStitch)**, ao qual integramos um sistema completo de download de capítulos aliado à fusão de duas excelentes ferramentas open-source de processamento:

- 🧵 **[SmartStitch](https://github.com/MechTechnology/SmartStitch)** — ferramenta inteligente para unir e cortar imagens de webtoons e manhwas com detecção avançada de pixels.
- 🖼️ **[Waifu2x-Extension-GUI](https://github.com/AaronFeng753/Waifu2x-Extension-GUI)** — software de upscaling de imagens com remoção de artefatos visuais e aumento de resolução via IA.

Partindo da estrutura do MedStitch para o processamento das imagens, o ReadStitch acopla um robusto sistema de download (com scrapers inteligentes, autenticação oculta sem navegador e suporte a dezenas de sites em EN, PT-BR, KR e JP), interligando as pontas para oferecer uma pipeline ponta a ponta: desde a extração automática dos capítulos na internet até a união, corte preciso e upscaling para leitura ou tradução.

---

## ✨ Funcionalidades

### 📥 Download de Raws
Baixe capítulos diretamente dos principais sites de leitura:

<table>
<tr>
<td valign="top">

#### 🇺🇸 Sites em Inglês (EN)

| Site | Suporte |
|---|---|
| [Asura Scans](https://asuracomic.net) | ✅ |
| [Webtoon (LINE)](https://www.webtoons.com) | ✅ |
| [QisManga](https://qismanga.com) | ✅ |
| [Comix](https://comix.jp) | ✅ |
| [Vortex / HiveToons](https://vortexscans.org) | ✅ |
| [Kagane](https://kagane.org) | ✅ |
| [Utoon](https://utoon.net) | ✅ |
| [GenzToons](https://genztoons.org) | ✅ |
| [Tapas](https://tapas.io) | ✅ |
| [RoliaScan](https://roliascan.com) | ✅ |
| [FlameComics](https://flamecomics.com) | ✅ |
| [ResetScans](https://reset-scans.org) | ✅ |
| [MangaDex](https://mangadex.org) | ✅ |
| [Elftoon](https://elftoon.com) | ✅ |
| [Comikey](https://comikey.com) | ✅ |
| [EzManga](https://ezmanga.org) | ✅ |

</td>
<td valign="top">

#### 🇧🇷 Sites em Português (PT-BR)

| Site | Suporte |
|---|---|
| [Verdinha](https://reaperscans.com.br) | ✅ *(login)* |
| [Mediocretoons](https://mediocrescan.com) | ✅ *(login)* |
| [Capitoons](https://capitoons.com) | ✅ |
| [Pluma Comics](https://plumacomics.com) | ✅ |
| [Geass Comics](https://geasscomics.com) | ✅ |
| [Lycan Toons](https://lycantoons.com) | ✅ |
| [Inkapk](https://inkapk.com) | ✅ |
| [Nexus (Nx-Toons)](https://nx-toons.com) | ✅ |
| [Hipercool / LerHentais](https://hiper.cool) | ✅ |
| [Vegitoons](https://vegitoons.com) | ✅ |
| [Astratoons](https://astratoons.com) | ✅ |
| [Safire Scan](https://safirescan.site) | ✅ |
| [Empreguetes](https://empreguetes.wtf) | ✅ |
| [Manhastro](https://manhastro.net) | ✅ |
| [Tiraninha](https://tiraninha.world) | ✅ |
| [OneReader](https://onereader.net) | ✅ |
| [Blackout Comics](https://blackoutcomics.com) | ✅ |
| [Erosect](https://erosect.xyz) | ✅ |
| [AniArgos](https://aniargos.com) | ✅ |
| [TiaManhwa](https://tiamanhwa.com) | ✅ |
| [MangaLivre.blog](https://mangalivre.blog) | ✅ |
| [Fenix Project](https://fenixproject.site) | ✅ |
| [Acervo Eremita](https://acervoeremita.com) | ✅ |
| [Império da Britannia](https://imperiodabritannia.net) | ✅ |
| [Nyx Scans](https://nyxscans.com) | ✅ |
| [NoxToons](https://noxtoons.com) | ✅ |

</td>
</tr>
<tr>
<td valign="top">

#### 🇰🇷 Sites Coreanos (KR)

| Site | Suporte |
|---|---|
| [Kakao Webtoon](https://webtoon.kakao.com) | ✅ |
| [Naver Webtoon](https://comic.naver.com) | ✅ |

</td>
<td valign="top">

#### 🇯🇵 Sites Japoneses (JP)

| Site | Suporte |
|---|---|
| [Piccoma](https://piccoma.com) | ✅ *(login)* |
| [Comic-Walker (Kadocomi)](https://comic-walker.com) | ✅ |

</td>
</tr>
</table>

> 💡 **Sites com login** exigem que você informe suas credenciais na aba **Baixador → Credenciais de Acesso**. O site é detectado automaticamente pela URL colada — não é necessário selecionar manualmente!

> 💡 **Quer pedir suporte para um novo site?** [Abra uma Issue](https://github.com/ReadStitch/ReadStitch/issues) descrevendo o site e ela será avaliada!

### 🧵 Unir e Cortar (Stitch + Slice)
Baseado no **SmartStitch**, o ReadStitch une imagens menores em uma tira longa e depois as fatia em dimensões ideais para leitura — evitando cortes no meio de painéis ou caixas de texto.

- **Detecção Avançada:** Algoritmos de comparação de pixels para cortes inteligentes.
- **Processamento em Lote:** Múltiplas pastas processadas simultaneamente.
- **Múltiplos Formatos:** `.png`, `.jpg`, `.webp`, `.bmp`, `.psd`, `.tiff` e `.tga`.

### 🖼️ Upscaling com Waifu2x
Baseado no **Waifu2x-Extension-GUI**, o ReadStitch aplica upscaling de imagens com inteligência artificial:

- Remoção de artefatos de compressão.
- Aumento de resolução sem perda de nitidez.
- Suporte a múltiplos modelos de IA.

### ⚙️ Outras Funcionalidades
- **Marcas d'água:** Inserção de overlay, cabeçalhos e rodapés automáticos.
- **Integração com o Windows:** Adicione o ReadStitch ao menu de contexto do Explorer.
- **Atualização Automática:** Sincronização com o repositório Git ou via releases.

---

## Como Utilizar

### Interface Gráfica (Releases)
1. Acesse a seção de [Releases](https://github.com/ReadStitch/ReadStitch/releases) e faça o download da versão mais recente.
2. Descompacte o arquivo e inicie o executável `ReadStitch.exe`.
3. Use a aba de **Download** para baixar raws de um site suportado.
4. Use a aba de **Processamento** para unir, cortar e aplicar upscaling nos capítulos.

### Rodando via Código-fonte
1. Instale o Python 3.11 ou superior.
2. Clone o repositório, crie um ambiente virtual e instale as dependências:
   ```bash
   git clone https://github.com/ReadStitch/ReadStitch.git
   cd ReadStitch
   
   # Crie o ambiente virtual
   python -m venv venv
   
   # Ative o ambiente virtual (Windows PowerShell)
   .\venv\Scripts\activate
   # Ou ative o ambiente virtual (Linux/Mac)
   # source venv/bin/activate
   
   # Instale as dependências
   pip install -r requirements.txt
   ```
3. Execute o programa (com o ambiente virtual ativo):
   ```bash
   # Interface gráfica
   python ReadStitchGUI.py

   # Modo console
   python ReadStitchConsole.py -i "./chapter" -sh 7500 -t .png
   ```

### Gerando o Executável (.exe)
Caso queira compilar o aplicativo após realizar modificações no código:
```bash
# Com o ambiente virtual ativado, rode o PyInstaller usando o arquivo .spec
pyinstaller ReadStitch.spec
```
O executável final e os arquivos necessários estarão disponíveis na pasta `dist/ReadStitch/`.

---

## Comandos do Console (CLI)

O modo console é recomendado para integrações e rotinas de automação:
```text
python ReadStitchConsole.py [-h] -i INPUT_FOLDER -sh SPLIT_HEIGHT
                             [-t {.png,.jpg,.webp,.bmp,.psd,.tiff,.tga}]
                             [-cw CUSTOM_WIDTH]
                             [-dt {none,pixel}]
                             [-s [0-100]]
                             [-lq [1-100]]
                             [-ip IGNORABLE_PIXELS]
                             [-sl [1-100]]
```

---

## Como Contribuir

O ReadStitch é um projeto de código aberto. Toda contribuição é bem-vinda!

- 🐛 **Relatar Problemas:** Crie uma [Issue](https://github.com/ReadStitch/ReadStitch/issues) descrevendo o problema, incluindo os passos de reprodução e os logs da pasta `__logs__`.
- 🌐 **Pedir Novo Site:** Quer que um site específico seja suportado no downloader? [Abra uma Issue](https://github.com/ReadStitch/ReadStitch/issues) com o nome e URL do site.
- 💡 **Sugestões:** Novas funcionalidades e melhorias são sempre bem-vindas no painel de Issues.
- 🔧 **Pull Requests:** Contribuições diretas no código podem ser feitas via Pull Request na branch principal.

---

## Créditos

Este projeto é construído a partir e em reconhecimento ao trabalho incrível dos seguintes repositórios e desenvolvedores:

- **[MedStitch](https://github.com/ViminioSM/MedStitch)** por **ViminioSM** — *Repositório base do qual partimos para integrar e construir todo o sistema robusto de download (scrapers).*
- **[waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan)** por **nihui** — *Responsável por reescrever o Waifu2x (original de **nagadomi**) para NCNN/Vulkan, permitindo que a IA rode de forma ultraleve e veloz por comando (CLI) em qualquer GPU sem depender de ambientes pesados ou CUDA.*
- **[SmartStitch](https://github.com/MechTechnology/SmartStitch)** por **MechTechnology**
- **[Waifu2x-Extension-GUI](https://github.com/AaronFeng753/Waifu2x-Extension-GUI)** por **AaronFeng753**
- **[Tachiyomi / Mihon](https://mihon.app)** — *Inspiração e referência na estrutura modular para scrapers e bypass de proteções de imagem.*
- E a toda a comunidade open-source e tradutores que colaboram relatando issues, aprimorando expressões regulares e mantendo os scrapers ativos!

---

## Licença

Este software é distribuído sob a licença MIT. Para mais informações, consulte o arquivo [LICENSE](LICENSE).
