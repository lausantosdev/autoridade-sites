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
- [x] Captura de leads via formulário WhatsApp + Cloudflare Worker + Supabase *(frontend integrado)*
- [~] Dashboard do empresário (visualização de leads em tempo real) *(existente — falta otimização e revisão)*
- [x] Wizard Web (FastAPI + WebSocket) com progresso em tempo real
- [x] Hero Image v2 — Atmosfera Aspiracional (16:9 com overlay refinado)
- [x] **Auditoria e correção de SEO nos footers** — link do logo em subpáginas corrigido (`#hero` → `index.html`), brand do footer vira link de retorno à home, CSS `.footer-logo` adicionado; links `servicos_footer` e `locais_footer` validados como 100% consistentes com os slugs dos arquivos gerados
- [x] **Otimização de Velocidade (Fase 1)** — Cache de Topics com TTL 7 dias + Paralelização de Hero/Home/Topics via `asyncio.gather` (server) e `ThreadPoolExecutor` (CLI). Ganho estimado: ~220s por geração. Frontend atualizado de 9→8 steps. *(Pendente: validação visual E2E)*

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

### Sprint: Finalização de Produto (Foco em Dashboard e Otimização Avançada)
> Foco: Finalizar dashboard do empresário e avaliar Otimização 3 (Dual Client).

- [ ] **Dashboard do empresário** — revisar, otimizar e validar com dados reais
- [ ] **Otimização de Velocidade (Fase 2)** — Dual Client / Split de Prompt (risco médio, requer avaliação de Qwen 3.6 Free)

---

## 📋 Backlog (Priorizado)

### 🟡 Alta Prioridade — Qualidade de Engenharia

> Spec detalhada em: `SPEC_POLIMENTO_TECNICO.md` (Aguardando slot de execução)
- [ ] `core/types.py` — TypedDict para contratos de dados (SiteConfig, SiteData, PageTemplate)
- [ ] Error handling granular no WebSocket (CONFIG_ERROR, API_ERROR, TEMPLATE_ERROR)
- [ ] Expansão de Coverage — `test_template_injector.py` + `test_server.py`
- [ ] Clean up — `ruff check --fix`
- [ ] **⏳ Validação visual E2E da paralelização** — regenerar site completo via Wizard e confirmar: (1) barra de progresso avança corretamente nos 8 steps, (2) imagem hero gerada, (3) home page premium renderizada, (4) tópicos aplicados nas subpáginas
- [ ] **⏳ Teste visual dos footers** — regenerar `darkbarbertwo.com.br` e verificar no browser: (1) links de serviços/cidades funcionam sem 404, (2) logo da subpágina leva para `index.html`, (3) brand do footer da subpágina leva para `index.html`, (4) `rel="nofollow"` no link da agência quando URL real for configurada

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
| Testes passando | 170 ✅ | > 0 falhas |
| Cobertura de testes | 79% | ≥ 75% |
| Rating de engenharia | 10/10 | 10/10 |
| CI (GitHub Actions) | ✅ verde | sempre verde |
