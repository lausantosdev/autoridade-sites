# SPEC — Sessão 1 (04/04/2026): Captura de Leads via Formulário

> **Atividade:** Captura de Leads — Frontend
> **Plano associado:** `PLAN_CAPTURA_LEADS_04_04_2026.md`
> **Arquivos principais:** `templates/page.html`, `templates/index.html`, `templates/js/widget.js`, `templates/css/style.css`, `core/template_injector.py`
> **Pré-requisito:** Pipeline de geração funcionando

---

## Sumário de Fases

- [ ] Fase 1: CSS do formulário de leads
- [ ] Fase 2: Templates (page.html + index.html) — CTA → form + links → #contato
- [ ] Fase 3: Reescrita do widget.js  
- [ ] Fase 4: Injeção na Home Premium (template_injector.py)
- [ ] Fase 5: Validação visual e E2E

---

## Fase 1 — CSS do Formulário de Leads

### 1.1 — Remover widget modal antigo de `style.css`

**Arquivo:** `templates/css/style.css`

**Remover** integralmente o bloco (linhas 1211-1332):
```css
/* WIDGET — Lead Capture Modal */
.aw-overlay { ... }
/* ... tudo até ... */
.aw-send:disabled { ... }
```

### 1.2 — Adicionar estilos do formulário de leads em `style.css`

**No mesmo arquivo**, no lugar do bloco removido, adicionar:

```css
/* ==========================================================================
   LEAD CAPTURE FORM — Embedded in CTA Section
   ========================================================================== */
.lead-form {
    max-width: 520px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.lead-form-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.lead-form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    text-align: left;
}

.lead-form-field label {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.7);
}

.lead-form-field input {
    padding: 14px 18px;
    border: 1.5px solid rgba(255, 255, 255, 0.15);
    border-radius: var(--radius, 12px);
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    font-family: var(--font, 'Inter', sans-serif);
    font-size: 1rem;
    transition: all 0.3s ease;
    outline: none;
}

.lead-form-field input::placeholder {
    color: rgba(255, 255, 255, 0.35);
}

.lead-form-field input:focus {
    border-color: #25d366;
    background: rgba(255, 255, 255, 0.12);
    box-shadow: 0 0 0 3px rgba(37, 211, 102, 0.15);
}

.btn-whatsapp {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 16px 32px;
    background: linear-gradient(135deg, #25d366, #128c7e);
    color: #ffffff;
    font-size: 1rem;
    font-weight: 700;
    border-radius: 50px;
    border: none;
    cursor: pointer;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 4px 20px rgba(37, 211, 102, 0.3);
    width: 100%;
    max-width: 360px;
    margin: 0 auto;
}

.btn-whatsapp:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 30px rgba(37, 211, 102, 0.45);
}

.btn-whatsapp:active {
    transform: scale(0.97);
}

.btn-whatsapp:disabled {
    opacity: 0.7;
    cursor: wait;
}

.btn-whatsapp i {
    font-size: 1.2em;
}

.lead-form-hint {
    font-size: 0.78rem;
    color: rgba(255, 255, 255, 0.45);
    text-align: center;
    margin: 0;
}

/* Light theme form overrides */
[data-theme="light"] .lead-form-field label {
    color: rgba(15, 23, 42, 0.6);
}

[data-theme="light"] .lead-form-field input {
    border-color: rgba(15, 23, 42, 0.15);
    background: rgba(15, 23, 42, 0.04);
    color: #0f172a;
}

[data-theme="light"] .lead-form-field input::placeholder {
    color: rgba(15, 23, 42, 0.3);
}

[data-theme="light"] .lead-form-field input:focus {
    border-color: #25d366;
    background: rgba(15, 23, 42, 0.06);
}

[data-theme="light"] .lead-form-hint {
    color: rgba(15, 23, 42, 0.45);
}

/* Mobile: stack form fields */
@media (max-width: 768px) {
    .lead-form-fields {
        grid-template-columns: 1fr;
    }
}
```

### 1.3 — Criar `widget.css` auto-contido

**Arquivo [NOVO]:** `templates/css/widget.css`

Conteúdo: exatamente os mesmos estilos de `.lead-form` acima, mas com **fallbacks explícitos** em todas as CSS variables. Será usado pela Home Premium via injeção.

```css
/* Autoridade Sites — Lead Capture Form (standalone, auto-contido) */
/* Usado na Home Premium (React) onde style.css não é carregado */

.lead-form { /* idêntico ao bloco acima */ }
/* ... todos os estilos com var(--nome, fallback) */
```

### Checkpoint Fase 1

- Abrir `templates/css/style.css` e confirmar que `.aw-*` sumiu e `.lead-form` existe
- Abrir `templates/css/widget.css` e confirmar que é auto-contido
- Rodar testes existentes — CSS não deve afetar nada:
```bash
pytest tests/ --cov=core --cov-fail-under=75
```

---

## Fase 2 — Templates (page.html + index.html)

### 2.1 — Subpágina: CTA vira formulário

**Arquivo:** `templates/page.html`

**Substituir** a seção CTA (linhas 124-135):

```html
<!-- ANTES -->
<section id="contato" class="cta-section">
    <div class="container">
        <h2 class="cta-title">@cta_titulo</h2>
        <p class="cta-subtitle">@cta_subtitulo</p>
        <div class="cta-buttons" style="justify-content: center;">
            <a href="@whatsapp_pagina" class="btn btn-white" target="_blank" rel="noopener">
                <i class="fab fa-whatsapp"></i> Fale Conosco
            </a>
        </div>
    </div>
</section>
```

```html
<!-- DEPOIS -->
<section id="contato" class="cta-section">
    <div class="container">
        <h2 class="cta-title">@cta_titulo</h2>
        <p class="cta-subtitle">@cta_subtitulo</p>
        <form id="lead-form" class="lead-form" autocomplete="on">
            <input type="hidden" name="keyword" value="@keyword">
            <input type="hidden" name="local" value="@local">
            <div class="lead-form-fields">
                <div class="lead-form-field">
                    <label for="lead-nome">Seu nome</label>
                    <input type="text" id="lead-nome" name="nome" placeholder="Como podemos te chamar?" required autocomplete="name">
                </div>
                <div class="lead-form-field">
                    <label for="lead-whatsapp">Seu WhatsApp</label>
                    <input type="tel" id="lead-whatsapp" name="whatsapp" placeholder="(11) 99999-9999" required autocomplete="tel">
                </div>
            </div>
            <button type="submit" class="btn btn-whatsapp">
                <i class="fab fa-whatsapp"></i> Iniciar Conversa pelo WhatsApp
            </button>
            <p class="lead-form-hint">Ao enviar, você será direcionado para o WhatsApp do especialista.</p>
        </form>
    </div>
</section>
```

### 2.2 — Subpágina: links WhatsApp viram #contato

**Arquivo:** `templates/page.html`

Alterar os seguintes `href`:

| Linha | Elemento | De | Para |
|---|---|---|---|
| ~75 | Hero CTA button | `@whatsapp_pagina` | `#contato` |
| ~117 | Authority CTA | `@whatsapp_pagina` | `#contato` |
| ~184 | SEO inline CTA | `@whatsapp_pagina` | `#contato` |
| ~244 | WhatsApp float | `@whatsapp_pagina` | `#contato` |

Também remover `target="_blank" rel="noopener"` desses links (agora são âncoras internas).

### 2.3 — Subpágina: adicionar `<link>` ao widget.css

**Arquivo:** `templates/page.html`, no `<head>` (após linha 28):
```html
<link rel="stylesheet" href="css/widget.css">
```

### 2.4 — Home fallback: mesmo tratamento

**Arquivo:** `templates/index.html`

- CTA section (linhas ~182-192) → substituir por formulário
- Links `{{whatsapp_link}}` nas linhas ~82, ~187, ~230 → `#contato`
- Adicionar `<link>` para `widget.css` no `<head>`

> **Nota:** A home fallback usa `{{whatsapp_link}}` enquanto as subpáginas usam `@whatsapp_pagina`. Os campos hidden no form usam `keyword=""` e `local=""` (vazios na home).

### Checkpoint Fase 2

- Abrir `templates/page.html` e confirmar:
  - Seção `#contato` tem `<form id="lead-form">`
  - Todos os href de WhatsApp apontam para `#contato`
  - Nenhum `target="_blank"` nos links de âncora
- Mesma validação para `templates/index.html`

---

## Fase 3 — Reescrita do `widget.js`

**Arquivo:** `templates/js/widget.js`

Reescrever completamente. Apagar todo o conteúdo (247 linhas) e substituir por:

```js
/**
 * Autoridade Sites — Lead Capture Form Handler
 * 
 * Fluxo: Form submit → POST Worker (se configurado) → WhatsApp redirect
 * 
 * Configuração esperada em window.AUTORIDADE_WIDGET:
 *   workerUrl, clientToken, dominio, empresaNome, whatsappNumero, keyword, local
 */
(function() {
    'use strict';

    var form = document.getElementById('lead-form');
    if (!form) return;

    var config = window.AUTORIDADE_WIDGET || {};

    // ===== 1. Form submit handler =====
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        var nomeInput = form.querySelector('[name="nome"]');
        var whatsappInput = form.querySelector('[name="whatsapp"]');
        var nome = nomeInput ? nomeInput.value.trim() : '';
        var whatsapp = whatsappInput ? whatsappInput.value.trim() : '';

        if (!nome || !whatsapp) return;

        // Validar WhatsApp (mínimo 8 dígitos)
        var digits = whatsapp.replace(/\D/g, '');
        if (digits.length < 8) {
            whatsappInput.setCustomValidity('Informe um número válido');
            whatsappInput.reportValidity();
            return;
        }
        whatsappInput.setCustomValidity('');

        // Feedback visual
        var btn = form.querySelector('button[type="submit"]');
        var originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fab fa-whatsapp"></i> Abrindo WhatsApp...';

        // POST para Worker (se configurado — fire-and-forget)
        if (config.workerUrl) {
            var keywordField = form.querySelector('[name="keyword"]');
            var localField = form.querySelector('[name="local"]');

            fetch(config.workerUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nome: nome,
                    whatsapp: whatsapp,
                    dominio: config.dominio || window.location.hostname,
                    pagina: window.location.pathname,
                    keyword: keywordField ? keywordField.value : (config.keyword || ''),
                    local: localField ? localField.value : (config.local || ''),
                    client_token: config.clientToken || ''
                })
            }).catch(function() { /* silencioso */ });
        }

        // Montar mensagem pré-preenchida para WhatsApp
        var keyword = config.keyword || '';
        var local = config.local || '';
        var contexto = '';
        if (keyword && local) {
            contexto = ' Vi o site sobre ' + keyword + ' em ' + local + ' e';
        }
        var msg = 'Olá, sou ' + nome + '.' + contexto +
                  ' gostaria de saber mais sobre os serviços.';

        var waUrl = 'https://wa.me/' + (config.whatsappNumero || '') +
                    '?text=' + encodeURIComponent(msg);

        // Abrir WhatsApp
        window.open(waUrl, '_blank');

        // Reset após 2s
        setTimeout(function() {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
            form.reset();
        }, 2000);
    });

    // ===== 2. Smooth scroll para âncoras #contato =====
    function setupSmoothScroll(link) {
        if (link.dataset.awScroll) return;
        link.dataset.awScroll = '1';
        link.addEventListener('click', function(e) {
            var target = document.getElementById('contato');
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // Links estáticos #contato
    document.querySelectorAll('a[href="#contato"]').forEach(setupSmoothScroll);

    // ===== 3. Observer para React: redireciona links wa.me dinâmicos =====
    function redirectDynamicWaLinks() {
        document.querySelectorAll('a[href*="wa.me"]:not([data-aw-redirect])').forEach(function(link) {
            link.dataset.awRedirect = '1';
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var target = document.getElementById('contato');
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    redirectDynamicWaLinks();

    // MutationObserver para capturar links criados pelo React
    if (typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(redirectDynamicWaLinks);
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Safety net
    setTimeout(redirectDynamicWaLinks, 500);
    setTimeout(redirectDynamicWaLinks, 1500);
})();
```

### Checkpoint Fase 3

Nenhum teste automatizado (JS puro). Validação será visual na Fase 5.

---

## Fase 4 — Injeção na Home Premium

### 4.1 — Nova função no `template_injector.py`

**Arquivo:** `core/template_injector.py`

Adicionar `_inject_leads_form(html, site_data)` que:

1. **Lê** `templates/css/widget.css` e injeta como `<link rel="stylesheet" href="css/widget.css">` antes de `</head>`
2. **Monta** o HTML do formulário usando dados de `site_data`:
   - `megaCtaSection.title` → título
   - `megaCtaSection.subtitle` → subtítulo
   - `leads.workerUrl`, `leads.clientToken` → config do widget
   - `empresa.telefoneWhatsapp` → número destino
   - `seo.keyword`, `seo.local` → atribuição
3. **Injeta** o `<section id="contato">` com o form ANTES de `</body>`
4. **Injeta** `<script>` com `window.AUTORIDADE_WIDGET` configurado
5. **Injeta** `<script src="js/widget.js"></script>`

> **Nota:** A função é chamada **sempre** (não apenas quando workerUrl está configurado). O widget.js já trata o caso sem workerUrl: não faz POST mas ainda redireciona para WhatsApp.

### 4.2 — Integrar no fluxo `inject_template()`

Após `_inject_footer_links_script()` (passo 4.1 existente), adicionar:

```python
# 4.2 Injetar formulário de captura de leads
html = _inject_leads_form(html, site_data)
```

### Checkpoint Fase 4

```bash
pytest tests/ --cov=core --cov-fail-under=75
```
Testes existentes não devem quebrar. Coverage não deve cair.

---

## Fase 5 — Validação Visual E2E

### 5.1 — Gerar site de teste

Usar config-test.yaml com `worker_url` mock. Gerar com:
```bash
python generate.py --config config-test.yaml
```

### 5.2 — Servir localmente

```bash
cd output/<dominio>
python -m http.server 8080
```

### 5.3 — Checklist de validação (usar browser_subagent)

**Subpágina (ex: `veterinario-campinas.html`):**
- [ ] Seção #contato exibe formulário com campos Nome e WhatsApp
- [ ] Botão tem gradiente verde WhatsApp
- [ ] Hero "Fale Conosco" faz smooth scroll até #contato
- [ ] Botão flutuante verde faz smooth scroll até #contato
- [ ] Inline CTA na zona SEO faz smooth scroll até #contato
- [ ] Preencher e submeter abre WhatsApp em nova aba
- [ ] Mensagem pré-preenchida contém nome + keyword + local
- [ ] Botão fica disabled 2s com "Abrindo WhatsApp..."
- [ ] Form reseta após submit

**Home Premium (`index.html`):**
- [ ] Seção #contato aparece acima do footer
- [ ] CTAs do React (renderizados pelo bundle) fazem scroll até o form
- [ ] Submit funciona igual à subpágina
- [ ] Estilos do form são consistentes com o design premium

**Mobile (viewport 400px):**
- [ ] Campos empilham verticalmente (1 coluna)
- [ ] Botão ocupa largura total
- [ ] Smooth scroll funciona no mobile

**Sem worker_url configurado:**
- [ ] Form funciona normalmente (abre WhatsApp)
- [ ] Nenhum erro no console do browser
- [ ] POST não é disparado (conferir via DevTools Network)

### Checkpoint Fase 5

> ✅ Todos os itens do checklist marcados como OK.

---

## Ordem de Execução

```
Fase 1 (CSS) → Fase 2 (Templates) → Fase 3 (widget.js) → Fase 4 (Injector) → Fase 5 (E2E)
```

**Regra:** Não avançar para a próxima fase sem o checkpoint anterior passar.
