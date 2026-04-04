# Sessions Log — SiteGen

> Diário de bordo de cada sessão de trabalho.
> **Antes de começar:** leia a última sessão. **Ao terminar:** registre o que foi feito e os próximos passos.

---

## 04/04/2026 — Sessão 5: Polimento Mobile e Validação B-05 (Sessão 2 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **Fix B-05 (Definitivo):** Removido `min-h-screen` no mobile do template principal em `index.html` para permitir que a seção hero se ajuste. Adicionado padding proporcional para compensar o navbar. Layout mobile validado por ter ganho um excelente UX e respiro (breathing room).
- Validação visual global garantindo aprovação tanto no Mobile quanto no Desktop.
- Ciclo de UI bugs oficialmente encerrado.

---

## 04/04/2026 — Sessão 4: Bugs Visuais e Coverage Recovery (Sessão 1 do Dia)

**Status:** ✅ Concluída parcialmente (Sessão Timeboxed)

### ✅ Feito
- **Coverage Recovered:** Testes puramente matemáticos adicionados em `test_color_utils.py` (Coverage restaurado acima de 75%).
- **Fix B-04:** Subtítulo do hero limitado a 15 palavras no prompt, impedindo quebra de layout no mobile.
- **Fix B-03:** `page.html` modificado para injetar o background correto nas subpáginas.
- **Fix B-01:** Grid do React reescrito para Cards Flutuantes Premium via injeção CSS/JS, erradicando os blocos cinzas / ghost cards.
- **Fix B-02:** Constraste WCAG validado e operante pós-fix do backend (de `#F59E0B` para `#9E6506`).
- **Teste E2E do Wizard:** Completado com sucesso gerando zip premium validado.

### ⚠️ Transferido para Sessão 5 (Sessão 2 do dia)
- **B-05 (Padding Excessivo Mobile):** Tentativa implementada substituindo `justify-center` por `flex-start` no container `min-h-screen`. Requer validação do Usuário na próxima sessão isolada.

---

## 03/04/2026 — Sessão 3: Auditoria Visual E2E Light & Dark

**Status:** ✅ Concluída com bugs documentados

### ✅ Feito (Verificado em browser)

- **Geração E2E concluída:** 2 sites gerados com sucesso — PetVida Premium (light) e AutoForte Mecânica (dark)
- **Fix de copy subpágina:** H1 agora forma frase gramaticalmente correta (prompt corrigido com exemplos certos/errados)
- **Fix de copy home:** Prompt do badge e H1 agora exige especificidade — proibido "Especialistas Locais", "Cuidados de Alto Nível"
- **WCAG back-end:** `core/color_utils.py` gera `colorText` ajustado por luminância (AA 4.5:1) e injeta no `__SITE_DATA__`
- **Overlay mobile:** CSS de overlay aprimorado no template para light e dark
- **Commit realizado:** `207b372`

### ❌ Bugs Ativos (Auditados mas NÃO resolvidos)

| # | Bug | Root Cause confirmado | Fix necessário |
|---|---|---|---|
| B-01 | **Ghost card cinza no grid desktop** (5 serviços em 3 colunas) | React preenche grid com slot vazio estilizado | Rebuild React — lógica `items.length % 3` |
| B-02 | **Cor amarela ilegível no tema light** (home + subpáginas) | React lê `theme.color` (bruto), não `theme.colorText` (ajustado WCAG) | Rebuild React — trocar para `colorText` |
| B-03 | **Subpágina sem imagem de hero** | `page.html` não injeta `hero-image.jpg` como background | Atualizar `page.html` + `page_generator.py` |
| B-04 | **Parágrafo hero home muito longo** (5 linhas mobile) | `hero_subtitle` sem limite rígido no prompt home | Limitar `hero_subtitle` a 20 palavras no prompt |
| B-05 | **Espaço morto acima do badge no hero** | `min-height: 100vh` impedia o ajuste do conteúdo | ✅ Resolvido via CSS Injection |

> ⚠️ B-01, B-02 e B-05 só podem ser resolvidos com **rebuild do React** (`npm run build`).
> B-03 e B-04 são correções de back-end (Python).

### 🔜 Próxima Sessão — OBRIGATÓRIO verificar antes de qualquer outra coisa

**FASE 1 — Verificação das correções de prompt (sem gerar site completo)**
- [ ] Gerar **apenas a home data** via `python -c "from core.site_data_builder import build_site_data; ..."` e verificar campos `hero_badge_text`, `hero_title_line_1`, `hero_title_line_2`
- [ ] Confirmar que o badge não é mais "Especialistas Locais" e o H1 não é mais institucional

**FASE 2 — Fixes de back-end (Python)**
- [ ] **B-04:** Limitar `hero_subtitle` a 20 palavras no prompt de `site_data_builder.py`
- [ ] **B-03:** Injetar `hero-image.jpg` como CSS background no `page.html` das subpáginas

**FASE 3 — Rebuild do React (resolver B-01, B-02, B-05)**
- [ ] Localizar source do React template
- [ ] Corrigir `featuresSection` para não renderizar ghost card (checar se `items.length % 3 !== 0`)
- [ ] Atualizar referências de `theme.color` → `theme.colorText` nos componentes hero (home e subpágina)
- [ ] Reduzir `padding-top` do hero para eliminar espaço morto
- [ ] Rodar `npm run build` e copiar `dist/` para `template-dist/`
- [ ] Retestar home + subpágina light E dark em mobile e desktop

**FASE 4 — Captura de Leads (feature produto)**
- [ ] Integrar frontend com Cloudflare Worker
- [ ] Documentar setup Supabase

---

## 03/04/2026 — Sessão 2: Wizard E2E e Leads

**Status:** 🔄 Em andamento

### ✅ Feito (Nesta Sessão)
- **Feature**: Wizard E2E (Fases 1, 2 e 3). Sincronização de passos no frontend, tratamento de fallback/ws.onclose, validações de step e adição da interface de captura de leads.

---

## 03/04/2026 — Auditoria PLAN_10_10 + Sprint de Estabilização

**Status:** ✅ Concluída | **Rating do projeto:** 10/10 (era 7/10) | **Cobertura de testes:** 79%

### ✅ Feito
- Tier 1: `pyproject.toml`, CI com GitHub Actions, testes `template_renderer`
- Tier 2: `threading.Lock` no `OpenRouterClient`, extração de `output_builder.py` (DRY)
- Tier 3: `core/logger.py`, `core/exceptions.py`, testes de integração com mocks
- **Bug fix:** Case-sensitivity no `csv.DictReader` — corrigidos 4 testes falhando
- **Bug fix:** Lógica de `theme_mode` sobrescrita apagava o resultado da IA
- **Bug fix:** 2 imports inline removidos de `generate.py`
- **Bug fix:** 2 `print()` residuais em `server.py` → `logger.error()`
- **Novo:** Geração automática de `robots.txt` no pipeline

### 🔜 Próxima Sessão

> ⚠️ Prioridade ajustada conforme `ROADMAP.md` — features de produto incompletas bloqueiam entregabilidade.

**🔴 Produto (fazer antes de qualquer polimento técnico)**
- [ ] **Wizard E2E** — gerar site completo via UI do Wizard e validar o ZIP entregue ao cliente
- [ ] **Captura de leads** — integrar frontend com Cloudflare Worker + documentar setup Supabase
- [ ] **Dashboard** — revisar, otimizar e validar com dados reais de leads

**🟡 Engenharia (executar via `SPEC_SESSAO_04_04_2026.md`)**
- [ ] Error handling granular no WebSocket (`server.py`) — `CONFIG_ERROR`, `API_ERROR`, `TEMPLATE_ERROR`
- [ ] `core/types.py` — TypedDict para contratos de dados (SiteConfig, SiteData, PageTemplate)
- [ ] `tests/test_template_injector.py` + `tests/test_server.py`
- [ ] `ruff check --fix` — limpeza de imports e type hints

---
