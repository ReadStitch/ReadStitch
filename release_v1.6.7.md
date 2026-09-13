<div align="center">
  <img src="https://raw.githubusercontent.com/ReadStitch/ReadStitch/refs/heads/master/assets/ReadStitchLogo.png" width="180" alt="ReadStitch Logo">
  <br>
  <h1>ReadStitch V1.6.7</h1>
</div>

---

## Novidades & Correções

- **Core / Utilitários (`uc_manager`):**
  - **Suporte a Perfis Persistentes:** O gerenciador central do `undetected_chromedriver` foi aprimorado para suportar diretórios de dados de usuário (`user_data_dir`), permitindo manter sessões de login ativas entre execuções sem acionar detecções de bot.
  - **Flexibilidade de Argumentos:** Adicionado suporte para passagem de argumentos extras (`extra_args`), viabilizando a injeção de flags essenciais (ex: `--disable-web-security`) de forma flexível em instâncias isoladas do navegador para burlar restrições de CORS (Tainted Canvas).

- **Correções Críticas nos Scrapers (da versão anterior):**
  - **Verdinha & Vegitoons:** Refatorados para acompanhar as recentes mudanças na API. Resolvido o problema de geração incorreta de links com `None` usando fallback inteligente no `obr_id`, e implementada a flag `is_wp` oficial para gerar os caminhos corretos.
  - **Pluma Comics:** Sistema de extração de imagens reescrito para lidar com a migração para Next.js (App Router).

- **Melhorias e Limpeza:**
  - Limpeza contínua do repositório: arquivos e diretórios de testes temporários (`scratch`, arquivos `.html`, etc.) utilizados nas sessões de debug foram excluídos da raiz, mantendo o ambiente limpo.

**Full Changelog**: https://github.com/ReadStitch/ReadStitch/compare/v1.6.6...v1.6.7
