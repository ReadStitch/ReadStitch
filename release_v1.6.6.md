<div align="center">
  <img src="https://raw.githubusercontent.com/ReadStitch/ReadStitch/refs/heads/master/assets/ReadStitchLogo.png" width="180" alt="ReadStitch Logo">
  <br>
  <h1>ReadStitch V1.6.6</h1>
</div>

---

## Novidades & Correções

- **Correções Críticas nos Scrapers:**
  - **Verdinha & Vegitoons:** Refatorados para acompanhar as recentes mudanças na API. Resolvido o problema de geração incorreta de links com `None` usando fallback inteligente no `obr_id`, e implementada a flag `is_wp` oficial para gerar os caminhos corretos tanto no novo CDN quanto nos diretórios legados WP-manga.
  - **Pluma Comics:** Sistema de extração de imagens reescrito. O site migrou para Next.js (App Router), e as imagens agora são resgatadas parseando os JSONs no lado do cliente com expressões regulares customizadas. A assinatura de segurança anti-hotlink da CDN (tokens `sig` e `expires`) agora é extraída corretamente para burlar bloqueios `HTTP 403 Forbidden`.

- **Melhorias e Limpeza:**
  - Limpeza completa do repositório: arquivos e diretórios de testes temporários (`scratch`, `test_out`, `test_lycantoons.py`, etc.) utilizados nas sessões de debug foram excluídos da raiz, otimizando o repositório.

**Full Changelog**: https://github.com/ReadStitch/ReadStitch/compare/v1.6.5...v1.6.6
