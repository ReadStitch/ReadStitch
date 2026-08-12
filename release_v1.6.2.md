<div align="center">
  <img src="https://raw.githubusercontent.com/ReadStitch/ReadStitch/refs/heads/master/assets/ReadStitchLogo.png" width="180" alt="ReadStitch Logo">
  <br>
  <h1>ReadStitch V1.6.2</h1>
</div>

---

## Novidades & Correções

- **Correção no Scraper (Drope Scan):**
  - Corrigido um bug onde todos os capítulos baixados da Drope Scan ficavam renomeados erroneamente como "Capítulo 1". Agora os números dos capítulos são extraídos e processados corretamente pela interface.

- **Correção no Scraper (Vegitoons):**
  - O scraper foi atualizado para lidar com a nova estrutura da API, que agora retorna as URLs das imagens como strings diretas ao invés de dicionários. Isso resolve os erros na hora de baixar imagens.

- **Novo Scraper (Hanami Heaven):**
  - Adicionado suporte nativo ao site Hanami Heaven (`https://hanamiheaven.org/`) para a extração de capítulos e imagens.

- **Remoção de Scraper:**
  - O scraper da **Utoon** foi removido, pois o site deixou de operar ou ser suportado.

**Full Changelog**: https://github.com/ReadStitch/ReadStitch/compare/v1.6.1...v1.6.2
