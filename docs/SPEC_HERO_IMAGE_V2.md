# SPEC: Hero Image v2 — Atmosfera Aspiracional

> **ID:** HERO-IMG-V2  
> **Prioridade:** Alta (impacto direto em conversão de leads)  
> **Estimativa:** ~30 minutos de implementação + ~5 min de regeneração de teste  
> **Criado:** 2026-04-05  

---

## Contexto e Problema

O sistema atual de geração de hero image (`core/imagen_client.py`) produz imagens focadas em **ferramentas e objetos do nicho** (ex: instrumentos cirúrgicos dentários). Isso gera medo/ansiedade no lead, reduzindo a taxa de conversão.

**Causa raiz identificada (3 falhas):**

1. **Prompt Engineering:** `CRITICAL RULE 1` manda a IA focar no "primary NON-HUMAN subject" do nicho → ferramentas
2. **Aspect Ratio:** `1:1` (quadrado) quando o hero section é landscape → crop severo, composição ruim
3. **CSS Overlay:** Opacidade mínima de apenas 25% no gradiente → imagem intimidadora muito visível

---

## Especificação Técnica

### 1. `core/imagen_client.py` — Prompt Rewrite

#### 1.1 Few-Shot Examples (`_SCENE_FEW_SHOT_EXAMPLES`)

**Filosofia:** Cada example foca no AMBIENTE/RESULTADO, nunca em ferramentas ou processo.

| Nicho | ANTES (ferramentas) | DEPOIS (ambiente aspiracional) |
|---|---|---|
| Odontologia | "dental chair in a high-tech clinic" | "spa-like waiting room, plush chairs, indoor plants, warm lighting — NO dental tools" |
| Mecânica | "luxury sports car in a garage" | "gleaming luxury car in a pristine showroom with polished floors" |
| Advocacia | "law book with wooden gavel" | "prestigious warm library with leather armchairs and golden ambient lighting" |
| Elétrica | "smart home electrical panel with circuits" | "modern smart home interior with subtle LED accent lighting" |

**Regra de ouro para novos examples:** Pergunte "o cliente gostaria de ESTAR nesse ambiente?" — se sim, é bom.

#### 1.2 System Prompt do LLM (`_generate_scene_description`)

Substituir:
```
"MUST strongly feature the primary NON-HUMAN subject of the niche"
```

Por:
```
"Focus on the ASPIRATIONAL OUTCOME or the WELCOMING ENVIRONMENT of the business."
"Show the RESULT the customer desires or the atmosphere they will experience — NOT the tools, equipment, or process."
"For health/medical niches: show serene, spa-like reception areas — NEVER clinical tools, needles, or surgical equipment."
```

#### 1.3 Prompt do Imagen (método `generate_hero`)

Alterações chave:
- Trocar "Show ONLY the environment, objects, tools" → "Focus on the WELCOMING ATMOSPHERE and ASPIRATIONAL RESULT — NOT on tools, sharp instruments, or clinical equipment"
- Trocar "ALL main subjects MUST be perfectly centered" → "Main subject in the center 50% of the frame. Outer 25% on each side must be heavily blurred (safe crop zone)"
- Trocar "cinematic, dramatic, moody" → "Cinematic, warm, inviting"
- Trocar "High-end premium corporate photography" → "High-end premium lifestyle photography, warm"

#### 1.4 Aspect Ratio

```python
# ANTES
aspect_ratio="1:1"

# DEPOIS
aspect_ratio="16:9"
```

---

### 2. `templates/css/style.css` — Overlay CSS

#### 2.1 Dark Overlay (`.hero-overlay`)

```css
/* ANTES: 50% → 25% → 60% → 100% */
/* DEPOIS: 70% → 55% → 70% → 100% */
.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        rgba(11, 13, 17, 0.7) 0%,
        rgba(11, 13, 17, 0.55) 30%,
        rgba(11, 13, 17, 0.7) 60%,
        var(--bg) 100%
    );
    z-index: 1;
}
```

#### 2.2 Light Overlay

```css
/* ANTES: 85% → 70% → 95% → 100% */
/* DEPOIS: 88% → 75% → 92% → 100% */
[data-theme="light"] .hero-overlay {
    background: linear-gradient(
        to bottom,
        rgba(255, 255, 255, 0.88) 0%,
        rgba(255, 255, 255, 0.75) 30%,
        rgba(255, 255, 255, 0.92) 60%,
        var(--bg) 100%
    ) !important;
}
```

#### 2.3 Gradiente CSS Fallback (`.hero`)

Adicionar `background-image` com gradiente radial sutil usando `--primary-rgb`. Será sobrescrito pelo inline `style="background-image: url(...)"` quando a imagem existir, mas aparece como fallback premium se:
- A imagem não existir
- A imagem demorar para carregar
- A imagem retornar 404

```css
.hero {
    /* ... propriedades existentes ... */
    background-image: 
        radial-gradient(ellipse at 30% 50%, rgba(var(--primary-rgb), 0.08) 0%, transparent 60%),
        radial-gradient(ellipse at 70% 30%, rgba(var(--primary-rgb), 0.05) 0%, transparent 50%);
}
```

---

### 3. Arquivos NÃO Alterados

| Arquivo | Motivo |
|---|---|
| `generate.py` | Pipeline já copia hero para ambos os caminhos |
| `templates/page.html` | Markup do hero não muda |
| `templates/index.html` | Markup do hero não muda |
| `core/template_injector.py` | Hero image path não muda |
| `core/output_builder.py` | Cópia de assets não muda |

---

## Checklist de Execução

```
[x] 1. Editar `core/imagen_client.py`:
    [x] 1.1 Reescrever `_SCENE_FEW_SHOT_EXAMPLES`
    [x] 1.2 Reescrever system_prompt em `_generate_scene_description`
    [x] 1.3 Reescrever prompt do Imagen em `generate_hero`
    [x] 1.4 Trocar `aspect_ratio` de "1:1" para "16:9"

[x] 2. Editar `templates/css/style.css`:
    [x] 2.1 Reforçar `.hero-overlay` (dark mode)
    [x] 2.2 Ajustar `[data-theme="light"] .hero-overlay`
    [x] 2.3 Adicionar gradiente fallback em `.hero`

[x] 3. Verificação:
    [x] 3.1 Rodar `pytest` — garantir zero falhas
    [x] 3.2 Deletar hero images do site de teste
    [x] 3.3 Regenerar via `python generate.py --step image`
    [x] 3.4 Validar visualmente no browser (mobile + desktop)
```

---

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| IA ainda gera ferramentas em edge cases | Baixa | Few-shot + negative instructions no prompt cobrem 95% dos nichos |
| Aspect ratio 16:9 corta demais no mobile portrait | Baixa | Safe crop zone (25% bordas desfocadas) + `background-position: center` |
| Overlay muito pesado esconde imagem demais | Mínima | Valores calibrados (55-70%) — imagem vira textura sutil, que é o objetivo |
| Testes quebram | Mínima | Sem mudança de interface pública |
