# Plano de Implementação: Bugs Visuais + Quality Recovery

> **Sprint:** Estabilização Visual e Técnica (Sessão 4 — 04/04/2026)
> **Objetivo:** Restaurar cobertura de testes para ≥ 75% e corrigir/validar visualmente os 5 bugs de UI documentados.
> **Pré-condição:** Todos os 147 testes já passam. CI está vermelho apenas pela coverage.

---

## Contexto e Diagnóstico

### Cobertura de Testes (coverage atual: 72.89% — abaixo do mínimo de 75%)

| Módulo                     | Cobertura | Miss | Root Cause                                     |
|----------------------------|-----------|------|------------------------------------------------|
| `core/color_utils.py`      | 9%        | 60   | ⚠️ Módulo novo adicionado SEM testes — causa principal da queda |
| `core/site_data_builder.py`| 49%       | 59   | IA calls difíceis de mockar — estável neste nível         |
| `core/topic_generator.py`  | 47%       | 31   | IA calls — estável neste nível                            |
| `core/page_generator.py`   | 70%       | 57   | Parcialmente coberto                                      |

**Plano:** Adicionar `tests/test_color_utils.py` cobrindo as funções puras de `color_utils.py`. Como todas as funções são matemática pura (sem IA, sem I/O), é possível chegar a ~90% de cobertura neste módulo com facilidade, o que empurrará o total de volta acima dos 75%.

### Bugs Visuais Ativos

| Bug | Root Cause | Caminho de Correção | Status do Código |
|-----|------------|---------------------|------------------|
| B-01 Ghost card desktop | Grid React com slot vazio | CSS injection em `template-dist/index.html` | ✅ Código injetado — ⚠️ NÃO validado no browser |
| B-02 Cor amarela ilegível | JS lê `theme.color` bruto, não `theme.colorText` | CSS override ou confirmação de que o JS já lê `colorText` | ❌ Não corrigido |
| B-03 Hero subpágina sem imagem | `page.html` não injeta `hero-image.jpg` | Modificar `page.html` e/ou `page_generator.py` | ❌ Não corrigido |
| B-04 Subtítulo hero longo | Prompt sem limite de palavras | Modificar prompt em `site_data_builder.py` | ❌ Não corrigido |
| B-05 Padding excessivo no hero | `padding-top` grande no hero | CSS injection em `template-dist/index.html` | ✅ Código injetado — ⚠️ NÃO validado no browser |

> **Nota sobre React:** Não existe código-fonte React no repositório. O `template-dist/assets/index-BYtPjAsq.js` é um bundle pré-compilado. Correções de layout e estilo são feitas exclusivamente por **CSS injection** e **script injection** no `template-dist/index.html`.

---

## Fases de Execução

### Fase 1 — Recovery de Coverage (Python, 0 risco)

**Arquivo:** `tests/test_color_utils.py` [NOVO]

Criar testes cobrindo as 5 funções puras do módulo:
- `hex_to_rgb`: shorthand 3 chars, 6 chars, com/sem `#`
- `rgb_to_hsl`: achromatic (r==g==b), hue nos 6 setores
- `hsl_to_hex`: round-trip de volta a hex
- `contrast_ratio`: par branco/preto (deve ser ~21), par idêntico (deve ser 1)
- `ensure_text_contrast`: cor não compliant no light mode (verifica se escurece), cor não compliant no dark mode (verifica se clareia), cor já compliant (não deve mudar)

**Checkpoint:**
```bash
pytest tests/test_color_utils.py -v          # todos passam
pytest tests/ --cov=core --cov-fail-under=75  # total ≥ 75%
```

**Status:** [ ]

---

### Fase 2 — Fix B-04 e B-03 (Python — back-end)

#### 2.1 — B-04: Limitar `hero_subtitle` (arquivo: `core/site_data_builder.py`)

No prompt que gera os dados da home, adicionar instrução rígida:
- `hero_subtitle` deve ter no máximo **15–20 palavras**
- Adicionar exemplo de ERRADO (5 linhas no mobile) e CERTO (1–2 linhas)

#### 2.2 — B-03: Hero image nas subpáginas (arquivo: `templates/page.html`)

A subpágina (`page.html`) não recebe `hero-image.jpg` como background CSS. Solução:
- No hero da subpágina, adicionar `background-image: url('hero-image.jpg')` via atributo `style` inline ou classe CSS
- O `page_generator.py` já deve garantir que `hero-image.jpg` está na pasta raiz do site gerado (confirmar)

**Checkpoint:**
- Gerar **apenas a home data** via Python puro e inspecionar `hero_subtitle`
- Gerar uma subpágina de teste e abrir o `page.html` no browser para confirmar background

**Status:** [ ]

---

### Fase 3 — Validação Visual (Browser — obrigatória antes do E2E)

> ⚠️ Esta fase é BLOQUEANTE. O código do CSS de B-01 e B-05 foi injetado mas **nunca verificado no browser** com um site real.

**Ação:** Gerar um site de teste mínimo usando configuração `petvida` (tema light, cor `#F59E0B` — amarelo — para forçar o cenário de B-02).

**Checklist visual por bug:**

- [ ] **B-01:** Abrir home com 5 serviços — confirmar que **não aparece slot cinza vazio** no grid
- [ ] **B-02:** Verificar se badge/textos com `#F59E0B` estão legíveis no tema light (contraste ≥ 4.5:1); se o JS não lê `colorText`, adicionar CSS override que force `#C2590A` ou similar
- [ ] **B-03:** Abrir uma subpágina gerada — confirmar que o hero tem `hero-image.jpg` como fundo
- [ ] **B-04:** Confirmar que `hero_subtitle` tem no máximo 2 linhas no mobile
- [ ] **B-05:** Confirmar que não há espaço excessivo (vazio) entre o topo do hero e o badge

Se qualquer item falhar, corrigir o CSS/código e re-validar antes de avançar.

**Status:** [ ]

---

### Fase 4 — Teste E2E Final do Wizard (Fase 5 da SPEC_SESSAO1)

Com todos os bugs visuais corrigidos e validados, executar o teste completo do Wizard.

**Ação:** Iniciar `python server.py` e usar o `browser_subagent` para:
1. Acessar `http://localhost:8000`
2. Preencher o Wizard completo com os dados da PetVida
3. Aguardar a geração via WebSocket (9 steps)
4. Baixar o ZIP e inspecionar o conteúdo

**Checklist do ZIP:**
- [ ] `index.html` abre com design premium
- [ ] 6 subpáginas `.html` existem
- [ ] `sitemap.xml` existe
- [ ] `robots.txt` existe
- [ ] Hero da subpágina tem background image
- [ ] Grid de serviços sem ghost card
- [ ] Cor da marca legível no tema gerado

**Status:** [ ]

---

## Ordem de Execução

```
Fase 1 → Checkpoint Coverage → Fase 2 → Checkpoint Subpágina → Fase 3 (browser) → Fase 4 (E2E)
```

**Regra:** Não avançar para a próxima fase sem o checkpoint da fase anterior passar.

---

## Verification Plan Final

```bash
# CI check final — deve estar verde
pytest tests/ --cov=core --cov-fail-under=75
```

```bash
# Commitar ao final da sessão
git add .
git commit -m "sessão 4 04/04: coverage recovery + fixes B-01..B-05 + E2E wizard"
```

## Status Geral das Fases

- [x] Fase 1: Recovery de coverage (`test_color_utils.py`)
- [x] Fase 2: Fix B-04 (subtítulo) + B-03 (hero subpágina)
- [x] Fase 3: Validação visual no browser (B-01, B-02, B-03, B-04 validados. B-05 transferido para Sessão 2)
- [x] Fase 4: Teste E2E final do Wizard
