# PLAN: Hero Image v2 — Atmosfera Aspiracional

> **Objetivo:** Reformular a geração de imagem hero e o design CSS do hero section para maximizar conversão de leads, eliminando imagens que causam medo/rejeição (ferramentas cirúrgicas, equipamentos intimidadores) e criando um sistema robusto e industrial que funcione para qualquer nicho.
> **Spec detalhada:** `SPEC_HERO_IMAGE_V2.md`
> **Criado:** 2026-04-05

---

## Diagnóstico do Problema

O sistema atual em `core/imagen_client.py` possui 3 falhas estruturais:

### 1. Prompt direciona para "ferramentas" em vez de "resultado"
```
CRITICAL RULE 1: The scene MUST strongly feature the primary NON-HUMAN subject of the niche
```
Para nichos como dentista, mecânica, etc., o "non-human subject" são as ferramentas — que causam medo.

### 2. Aspect ratio errado
```python
aspect_ratio="1:1"  # ← Quadrado, mas o hero é landscape
```
Uma imagem 1:1 sofre crop severo em `background-size: cover` em viewports landscape (desktop). A composição nunca fica ideal.

### 3. Overlay insuficiente (dark mode)
```css
.hero-overlay {
    background: linear-gradient(
        to bottom,
        rgba(11, 13, 17, 0.5) 0%,      /* ← apenas 50% */
        rgba(11, 13, 17, 0.25) 35%,     /* ← apenas 25%! */
        rgba(11, 13, 17, 0.6) 65%,
        var(--bg) 100%
    );
}
```
O ponto médio (35%) tem apenas 25% de opacidade — a imagem fica muito visível, expondo detalhes intimidadores.

---

## Decisão de Design

- **Manter proibição de rostos humanos** — rostos gerados por IA sofrem crop imprevisível em `background-size: cover` em diferentes viewports (cabeças cortadas).
- **Redirecionar foco:** de "ferramentas/objetos do nicho" para "ambiente acolhedor + resultado aspiracional".
- **Imagem como textura, não protagonista:** overlay pesado (~70%) transforma a imagem em mood setter sutil.
- **Fallback premium:** gradiente CSS garante visual premium mesmo sem imagem.

---

## Proposed Changes

### Componente 1: Prompt Engineering (`core/imagen_client.py`)

| Mudança | Linhas | O quê |
|---|---|---|
| 1.1 | 17-26 | Reescrever `_SCENE_FEW_SHOT_EXAMPLES` — foco em ambientes acolhedores |
| 1.2 | 36-41 | Reescrever system prompt — de "non-human subject" para "aspirational outcome" |
| 1.3 | 106-118 | Reescrever prompt do Imagen — warm/inviting, safe crop zone |
| 1.4 | 129 | Trocar `aspect_ratio` de `"1:1"` para `"16:9"` |

### Componente 2: CSS Overlay Reforçado (`templates/css/style.css`)

| Mudança | Linhas | O quê |
|---|---|---|
| 2.1 | 291-302 | Reforçar `.hero-overlay` dark (55-70% opacidade) |
| 2.2 | 89-97 | Ajustar `[data-theme="light"] .hero-overlay` (75-92%) |
| 2.3 | 268 | Adicionar gradiente radial CSS como fallback premium em `.hero` |

### Componente 3: Pipeline (`generate.py`)

Nenhuma mudança necessária — pipeline já copia hero para ambos os paths.

---

## Impacto nos Templates

| Template | Usa hero como | Mudança necessária |
|---|---|---|
| `page.html` (subpáginas) | `background-image: url('images/hero.jpg')` inline | **Nenhuma** |
| `index.html` (home HTML fallback) | `background-image: url('images/hero.jpg')` inline | **Nenhuma** |
| React Home (template-dist) | `hero-image.jpg` via `heroImagePath` no SiteData | **Nenhuma** |

---

## Resumo de Arquivos Alterados

| Arquivo | O quê | Risco |
|---|---|---|
| `core/imagen_client.py` | Rewrite prompts + few-shots + aspect ratio | Baixo (só afeta gerações futuras) |
| `templates/css/style.css` | Overlay mais opaco + gradiente fallback | Baixo (melhoria visual pura) |

---

## Regeneração Necessária

Após aplicar as mudanças, as imagens hero existentes NÃO serão substituídas automaticamente (o pipeline pula geração se o arquivo já existe). Será preciso deletar `hero-image.jpg` e `images/hero.jpg` manualmente no output do site de teste para regenerar.

---

## Verification Plan

### Automated Tests
- Rodar `pytest` — garantir zero falhas
- Validar que `imagen_client.py` mantém a interface pública (`generate_hero()`)

### Manual Verification
1. Deletar `output/meudentistatest.com.br/hero-image.jpg` e `images/hero.jpg`
2. Rodar `python generate.py --step image --config config.yaml`
3. Verificar visualmente no browser (localhost:8081):
   - Imagem mostra **ambiente acolhedor** (não ferramentas)
   - Overlay escurece suficiente para texto legível
   - Gradiente fallback aparece se imagem removida
4. Testar em viewport mobile (375px) e desktop (1440px) para validar crop
