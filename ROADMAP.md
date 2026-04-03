# Roadmap — SiteGen (Autoridade Sites)

> **Produto:** Gerador automático de sites SEO para negócios locais brasileiros.
> **Visão:** Gerar um site premium completo por ~R$0,03 em minutos, pronto para deploy e conversão.

---

## ✅ Entregue (Histórico)

### Produto Core
- [x] Pipeline de geração completo (9 etapas: config → mix → sitemap → image → home → topics → pages → validate → zip)
- [x] Home page premium com template React pré-buildado (sem Node em produção)
- [x] Subpáginas SEO geradas via IA (keyword × localidade, ~1500 palavras cada)
- [x] Geração paralela com até 30 workers + retry automático com validação inline
- [x] Hero image gerada via Google Imagen (IA)
- [x] Tema light/dark resolvido por IA ou config manual
- [x] Schema JSON-LD (LocalBusiness + FAQPage) injetado automaticamente
- [x] Sitemap XML + mapa-do-site.html gerados automaticamente
- [x] `robots.txt` gerado automaticamente no pipeline
- [x] Footer com links SEO geo-localizados (silo de links internos)
- [~] Captura de leads via formulário WhatsApp + Cloudflare Worker + Supabase *(backend ok — falta frontend integrado e configs manuais do Cloudflare/Supabase)*
- [~] Dashboard do empresário (visualização de leads em tempo real) *(existente — falta otimização e revisão)*
- [~] Wizard Web (FastAPI + WebSocket) com progresso em tempo real *(funcional — falta otimização, revisão e teste de geração E2E real)*

### Engenharia / Qualidade (PLAN_10_10 — Concluído em 03/04/2026)
- [x] Logging estruturado em todo o `core/` (`core/logger.py`)
- [x] Exceções customizadas (`core/exceptions.py`: ConfigError, APIError, TemplateError, ValidationError)
- [x] Thread-safety no `OpenRouterClient` (`threading.Lock`)
- [x] Extração de `core/output_builder.py` (DRY entre CLI e Wizard)
- [x] `pyproject.toml` com gestão formal de dependências
- [x] CI com GitHub Actions (lint + testes + coverage ≥ 75%)
- [x] Cobertura de testes: **79%** (136 testes passando)
- [x] Fix bug CSV parser (case-sensitivity no `DictReader`)
- [x] Fix bug `theme_mode` sobrescrito pelo fallback

---

## 🚧 Em Progresso

### Sprint: Polimento Estrutural (Sessão: 04/04/2026)
> Spec detalhada em: `SPEC_SESSAO_04_04_2026.md`

- [ ] `core/types.py` — TypedDict para contratos de dados (SiteConfig, SiteData, PageTemplate)
- [ ] Error handling granular no WebSocket (CONFIG_ERROR, API_ERROR, TEMPLATE_ERROR)
- [ ] `tests/test_template_injector.py` — cobertura das funções puras de injeção
- [ ] `tests/test_server.py` — FastAPI TestClient (path traversal, 404)
- [ ] `ruff check --fix` — limpeza de imports e type hints

---

## 📋 Backlog (Priorizado)

### 🔴 Alta Prioridade — Features Incompletas (Produto não está 100% entregável)

- [ ] **Captura de leads** — integrar frontend com Cloudflare Worker + documentar setup manual do Supabase
- [ ] **Dashboard do empresário** — revisar, otimizar e validar com dados reais
- [ ] **Wizard Web** — teste de geração E2E real (gerar site completo via UI e validar o ZIP)

### 🟡 Alta Prioridade — Qualidade de Engenharia (Próximas 2-3 sessões)
- [ ] **Monitoramento em produção** (Sentry ou similar) — rastrear erros reais em deploy
- [ ] **Script de deploy automático** — rsync / FTP / Cloudflare Pages com um comando
- [ ] **Testes E2E do pipeline** — fixtures com config real, sem chamar APIs externas

### Média Prioridade
- [ ] **Multi-cliente / modo batch** — gerar N sites de uma vez com configs diferentes
- [ ] **Cache inteligente de IA** — não regenerar conteúdo se config não mudou
- [ ] **Relatório de qualidade visual** — exportar PDF/HTML com métricas de cada site gerado
- [ ] **Suporte a mais modelos de IA** — Claude, GPT-4o além de DeepSeek

### Baixa Prioridade / Futuro
- [ ] **Dashboard SaaS** — multi-operador com autenticação e fila de geração
- [ ] **Template alternativo mobile-first** — segundo tema além do atual dark-mode React
- [ ] **Integração Google Search Console** — monitorar indexação dos sites gerados
- [ ] **API REST pública** — para integrações com CRM e sistemas dos clientes

---

## Métricas de Saúde

| Indicador | Status | Meta |
|---|---|---|
| Custo por site | ~R$0,03 | < R$0,10 |
| Testes passando | 136 ✅ | > 0 falhas |
| Cobertura de testes | 79% | ≥ 75% |
| Rating de engenharia | 10/10 | 10/10 |
| CI (GitHub Actions) | ✅ verde | sempre verde |
