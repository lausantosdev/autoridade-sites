# Sessions Log — SiteGen

> Diário de bordo de cada sessão de trabalho.
> **Antes de começar:** leia a última sessão. **Ao terminar:** registre o que foi feito e os próximos passos.

---

## 05/04/2026 — Sessão 13: Hero Image v2 - Atmosfera Aspiracional (Sessão 5 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **Prompt Engineering Atualizado:** Modificado o `core/imagen_client.py` para reforçar a proibição de rostos e substituir o foco em ferramentas intimidantes por "Atmosfera Aspiracional" e "Ambiente Acolhedor".
- **Hero Image Ratio Corrigido:** Alterada a solicitação da Imagem Hero do padrão `1:1` para `16:9`, aprimorando muito o visual em desktop (Landscape) sem os cortes extremos do `background-size: cover`.
- **Overlay Dinâmico (CSS) Reforçado:** Aumentadas as opacidades nos sobretons (`style.css`), do dark (25%->55%) e do light, assegurando ótima legibilidade dos subtítulos ao fundo perante o contrast checking, sem ofuscar a experiência do site.
- **Fallback Premium:** Aplicado um `radial-gradient` sutil na classe base `.hero` como fallback nativo (antes da imagem estourar na tela), entregando um design mais preenchido em redes lentas ou falhas.
- **Testes Validados:** Teste regressivo `pytest` com sucesso + Regeneração End-to-End da feature image confirmando adequação completa do Output.

### 🔜 Próxima Sessão
- Otimização de Velocidade — Paralelização (Cache Topics, Gathers no Server) e Split de Prompts.
- Dashboard do empresário.

---

## 05/04/2026 — Sessão 12: E2E Captura de Leads e Ajustes de Âncora (Sessão 4 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **E2E Captura de Leads Concluído:** Finalização e validação manual completa do Form injection na Home e layout na subpágina. Produto Core Entregue.
- **Scroll Margin Global:** Corrigido bug visual do Header Fixo nativo bloqueando os subtítulos onde quer que uma hashtag âncora fosse engatilhada (seja em links `.wa.me`, `#sobre`, ou menu Hambúrguer), fixado universalmente via `scroll-margin-top`.

### 🔜 Próxima Sessão
- Partir para a execução **Plano de Otimização de Velocidade (Paralelização)** que arquivamos como `Implementation Plan`.
- Validar se a instabilidade do Qwen Free suportará o fluxo ou se os Fallbacks rápidos no Gemini Action funcionarão liso.

---

## 05/04/2026 — Sessão 11: Refinamento UX Home e Optimizations Speed (Sessão 3 do dia)

**Status:** ✅ Concluída — `5be6a1b`

### ✅ Feito
- **Design Premium Home:** Implementadas linhas separadoras e fundo sutil na Home igualando a subpágina, adaptando a cor ao `var(--theme-color)`.
- **Mini-CTA Bottom:** Fomos além das subpáginas. Inseriu `bottom-cta` idêntica às subpáginas antes do footer da Home (React).
- **Smooth Scroll FOUC & Margin:** Botões dinâmicos de wa.me e header navegando limpos para `#contato` via Scroll-margin e sem glitch visual pré-JS (display none CSS injetado).
- **Speed Optimization Brainstorm:** Documentada (`docs/SPEED_OPTIMIZATION_BRAINSTORM.md`) a rota para paralelização com Cache de Topics, Async Gather de Hero e Call Duplo com Qwen 3.6 Plus (Free) de fallback no Qwen para abater custos logísticos e derrubar de minutos para segundos o processo.

---

## 05/04/2026 — Sessão 10: Estabilidade da API e Fix de Timeout (Sessão 2 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **Fix de Hang Silencioso:** Diagnosticada cadeia de vulnerabilidades no Client da API durante a geração de SEO.
- **Camada 1 (HTTP):** Adicionado `HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0...)` no `OpenRouterClient` para prevenir travamentos de I/O em chunks lentos.
- **Camada 2 (Executors):** Adicionado `as_completed(timeout=MAX)` e timeouts individuais por proxy na geração de páginas para não travar a pool.
- **Camada 3 (Server):** Adicionado daemon threads e loop de deadline no WebSocket. Agora o frontend expira limpo se a API escalar os tempos e a geração ficar inviável, no lugar de bloquear eternamente.

### 🔜 Próxima Sessão
- Exigir e colher o feedback do Usuário sobre a página Home (React) que foi mockada no `.zip` gerado com a Injeção de Captura de Leads.
- Repassar fluxos vitais do Workflow.

---

## 05/04/2026 — Sessão 9: UX Formulário de Leads — Home React (Sessão 1 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- Pipeline testado injetando perfeitamente a captura de leads na Home React.
- Esvaziada a Section original da MegaCTA e movida a Section #contato (CSS puro injetado na Fase 4) para a sua localização sem gerar grids vazias ou conflitos com o React.
- Validação pelo HTML de compilação da pipeline: injetou o `leads-home-integrator.js` corretamente.

---

## 04/04/2026 — Sessão 8: UX Formulário de Leads — Subpáginas OK (Sessão 5 do dia)

**Status:** ✅ Commited — `a0bb9bf`

### ✅ Feito
- **widget.css:** Card branco sólido, botão cinza inativo → verde ao preencher nome+whatsapp (CSS `:valid`)
- **widget.js:** Validação customizada: mensagem de erro contextual + borda vermelha + animação shake nos campos vazios
- **style.css:** Sincronização dos estilos de validação + `scroll-margin-top: 72px` no `#contato` (corrige corte do título ao ancorar via link)
- **page.html:** Título CTA substituído por `Fale Conosco` + subtítulo suave (não pressiona agendamento)
- **index.html (template):** Idem ao page.html
- **Teste E2E from scratch:** Pipeline regenerado do zero, encoding UTF-8 correto validado

### ⚠️ Pendente — HOME (index.html gerado pelo React)
- O formulário da home usa `frontend/src/components/ContactForm.jsx` (React), **não** o `page.html`
- Problemas observados no mobile: form card transbordando/flutuando fora dos limites da seção; título "Agende" ainda não substituído por "Fale Conosco"
- **Próximo passo:** Localizar e editar `ContactForm.jsx` + CSS correspondente na pasta `frontend/`

---

## 04/04/2026 — Sessão 7: Especificação Captura de Leads (Sessão 4 do dia)

**Status:** 🔄 Em andamento

### ✅ Feito
- **Análise & Brainstorm:** Revisão da UX do widget original de interceptação modal, substituído arquiteturalmente pelo padrão de Formulário Embutido.
- **Plano Aprovado (Opção C):** Focar na captação 100% dos usuários que chamam o contato com design mais fluído e orgânico e fallback sem bloquear WhatsApp.
- **Specs Criadas:** `PLAN_CAPTURA_LEADS_04_04_2026.md` e `SPEC_SESSAO1_04_04_2026.md` disponíveis no diretório `docs/captura-leads/`.
- **Roadmap:** Atualizado para refletir o ínicio iminente da execução da Fase 1 (CSS).

### 🔜 Próxima Sessão (Imediato)
- Executar e validar Fase 1: CSS (arquivo `widget.css` auto-contido e ajustes em `style.css`).
- Executar Fase 2: Templates (ajuste de page.html e index.html com `<form>`).
- Executar Fase 3: js rewrite e Fase 4: Template Injector.

---

## 04/04/2026 — Sessão 6: Conclusão Teste E2E do Wizard (Sessão 3 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **Feature Finalizada:** Teste E2E completo do Wizard validado pelo usuário de forma manual e visual. Todo o fluxo funcionando 100% e entrega finalizada.
- Atividade `wizard-e2e` marcada como 100% concluída nos planos de implementação.

### 🔜 Próxima Sessão
- **Captura de leads** — integrar frontend com Cloudflare Worker + documentar setup manual do Supabase.
- **Dashboard do empresário** — revisar, otimizar e validar com dados reais.

---

## 04/04/2026 — Sessão 5: Polimento Mobile e Validação B-05 (Sessão 2 do dia)

**Status:** ✅ Concluída

### ✅ Feito
- **Fix B-05 (Definitivo):** Removido `min-h-screen` no mobile do template principal em `index.html` para permitir que a seção hero se ajuste. Adicionado padding proporcional para compensar o navbar. Layout mobile validado por ter ganho um excelente UX e respiro (breathing room).
- **Refinamento Final B-05:** Ajuste de padding-top do hero mobile de 5rem para 3.5rem, garantindo alinhamento e consistência fina com as subpáginas.
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
