# Plano de Implementação: Captura de Leads via Formulário

> **Sprint:** Finalização de Produto
> **Atividade:** `captura-leads`
> **Objetivo:** Substituir o botão direto do WhatsApp por um formulário embutido na página que captura nome + telefone, salva no Supabase e redireciona para o WhatsApp com mensagem pré-preenchida.

---

## Contexto e Motivação

O consultor de marketing (operador do SiteGen) precisa **comprovar ROI mensalmente** para os empresários. Dados de clique não bastam — são necessários **nome + telefone + atribuição** (de qual página/keyword/cidade veio o lead) em uma base de dados **independente** (Supabase), sem depender do empresário.

### Solução aprovada: Formulário embutido na seção CTA

Todos os CTAs de WhatsApp (hero, inline, floating button) passam a redirecionar para `#contato` via smooth scroll. A seção CTA vira um formulário com 2 campos:

```
┌──────────────────────────────────────┐
│     Solicite seu Orçamento           │
│  Preencha e fale direto pelo WhatsApp│
│                                      │
│  Nome:     [________________________]│
│  WhatsApp: [________________________]│
│                                      │
│  [📱 Iniciar Conversa pelo WhatsApp] │
│                                      │
│  Ao enviar, você será direcionado    │
│  para o WhatsApp do especialista.    │
└──────────────────────────────────────┘
```

**Fluxo:** Submit → POST Worker (se configurado) → `window.open(wa.me/...?text=Olá, sou Maria...)`.

---

## Diagnóstico: O que existe vs o que muda

| Peça | Antes | Depois |
|---|---|---|
| Seção CTA (subpáginas) | Botão direto `wa.me` | Formulário nome + WhatsApp |
| Seção CTA (home fallback) | Botão direto `wa.me` | Formulário nome + WhatsApp |
| Home Premium (React) | Botão direto via React | Form injetado por `template_injector.py` |
| Botão flutuante WhatsApp | `href="wa.me/..."` | `href="#contato"` (scroll suave) |
| Hero CTA | `href="wa.me/..."` | `href="#contato"` (scroll suave) |
| Inline CTA (zona SEO) | `href="wa.me/..."` | `href="#contato"` (scroll suave) |
| `widget.js` | Interceptor modal 2-passos | Handler de form submit |
| Widget CSS (`.aw-*`) | Modal overlay no `style.css` | Removido — substituído por estilos de form |
| `template_injector.py` | Não injeta widget | Injeta form + CSS + JS na Home Premium |

---

## Fases de Execução

### Fase 1 — CSS do formulário de leads

**Arquivo:** `templates/css/style.css`

- **Remover** bloco inteiro do `/* WIDGET — Lead Capture Modal */` (linhas 1211-1332)
- **Adicionar** novo bloco `/* LEAD CAPTURE FORM */` com estilos para `.lead-form`, `.lead-form-fields`, `.lead-form input`, `.lead-form-hint`
- Estilos usam CSS variables (`var(--primary)`, `var(--bg-card)`) para compatibilidade com light/dark
- Dois campos lado a lado no desktop, empilhados no mobile
- Botão submit com cor verde WhatsApp para reforçar destino
- Animação sutil de focus nos inputs

**Arquivo [NOVO]:** `templates/css/widget.css`

- Cópia auto-contida dos mesmos estilos de form, mas com **fallbacks** em todas as variáveis (para funcionar na Home Premium que não carrega `style.css`)
- Usado exclusivamente pela injeção do `template_injector.py`

**Status:** [x]

---

### Fase 2 — Templates das subpáginas

**Arquivo:** `templates/page.html`

2.1 — **Substituir** a seção CTA (linhas 124-135) por formulário:
```html
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

2.2 — **Alterar** todos os `href="@whatsapp_pagina"` para `href="#contato"` (hero, inline CTA, float):
  - Linha 75 (hero button)
  - Linha 117 (authority section)
  - Linha 184 (SEO inline CTA)
  - Linha 244 (WhatsApp float)

2.3 — Manter `target="_blank"` removido nos links acima (agora são âncoras internas)

**Arquivo:** `templates/index.html` (home fallback)

- Mesmo tratamento: CTA vira form, links viram `#contato`
- Linhas 82, 187, 230 (hero, CTA button, float)

**Status:** [x]

---

### Fase 3 — Reescrita do `widget.js`

**Arquivo:** `templates/js/widget.js`

Reescrita total. O script vira um handler de formulário (não mais um interceptor de links):

```js
(function() {
    'use strict';
    
    var form = document.getElementById('lead-form');
    if (!form) return;
    
    var config = window.AUTORIDADE_WIDGET || {};
    
    // 1. Form submit handler
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        var nome = form.querySelector('[name="nome"]').value.trim();
        var whatsapp = form.querySelector('[name="whatsapp"]').value.trim();
        if (!nome || !whatsapp) return;
        
        // Feedback visual
        var btn = form.querySelector('button[type="submit"]');
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fab fa-whatsapp"></i> Abrindo WhatsApp...';
        
        // POST para Worker (se configurado)
        if (config.workerUrl) {
            fetch(config.workerUrl, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    nome: nome,
                    whatsapp: whatsapp,
                    dominio: config.dominio || '',
                    pagina: window.location.pathname,
                    keyword: form.querySelector('[name="keyword"]')
                             ? form.querySelector('[name="keyword"]').value : '',
                    local: form.querySelector('[name="local"]')
                           ? form.querySelector('[name="local"]').value : '',
                    client_token: config.clientToken || ''
                })
            }).catch(function() {});
        }
        
        // Montar mensagem pré-preenchida
        var local = config.local || '';
        var keyword = config.keyword || '';
        var contexto = (keyword && local) 
            ? ' Vi seu site sobre ' + keyword + ' em ' + local + '.'
            : '';
        var msg = 'Olá, sou ' + nome + '.' + contexto + 
                  ' Gostaria de saber mais sobre os serviços.';
        var url = 'https://wa.me/' + (config.whatsappNumero || '') + 
                  '?text=' + encodeURIComponent(msg);
        
        window.open(url, '_blank');
        
        // Reset
        setTimeout(function() {
            btn.disabled = false;
            btn.innerHTML = originalText;
            form.reset();
        }, 2000);
    });
    
    // 2. Smooth scroll para #contato em links wa.me estáticos
    document.querySelectorAll('a[href="#contato"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('contato').scrollIntoView({behavior: 'smooth'});
        });
    });
    
    // 3. Observer para React: redireciona links wa.me dinâmicos para #contato
    function redirectWaLinks() {
        document.querySelectorAll('a[href*="wa.me"]:not([data-aw])').forEach(function(link) {
            link.dataset.aw = '1';
            link.addEventListener('click', function(e) {
                e.preventDefault();
                document.getElementById('contato').scrollIntoView({behavior: 'smooth'});
            });
        });
    }
    redirectWaLinks();
    
    var observer = new MutationObserver(redirectWaLinks);
    observer.observe(document.body, {childList: true, subtree: true});
})();
```

**Decisão arquitetural:** O form **sempre funciona** (redireciona para WhatsApp com mensagem pré-preenchida). O POST para o Worker é **condicional** (`if config.workerUrl`). Isso significa que mesmo sem backend de tracking, o form agrega valor (mensagem personalizada pro empresário).

**Status:** [x]

---

### Fase 4 — Injeção na Home Premium

**Arquivo:** `core/template_injector.py`

Adicionar função `_inject_leads_form()` ao pipeline de injeção.

**Lógica:**
1. Lê `templates/css/widget.css` e injeta como `<style>` inline antes de `</head>`
2. Injeta `<section id="contato">` com o formulário completo antes de `</body>`
3. Injeta `<script>` configurando `window.AUTORIDADE_WIDGET` com dados de `site_data`
4. Injeta `<script src="js/widget.js"></script>`

**Ordem no `inject_template()`:**
```
1. _inject_meta_tags()
2. _inject_schema()
3. _inject_site_data()
4. _inject_footer_links_script()
5. _inject_leads_form()     ← NOVO
6. _copy_assets()
```

O formulário na Home Premium usa dados do `site_data.megaCtaSection` para título/subtítulo, mantendo consistência com o conteúdo gerado pela IA.

**Status:** [x]

---

### Fase 5 — Validação visual e E2E

5.1 — Gerar site teste com `worker_url` mock no config
5.2 — Servir localmente
5.3 — Checklist:

**Subpágina:**
- [ ] Seção CTA mostra formulário com 2 campos
- [ ] Clicar no hero "Fale Conosco" faz scroll suave até #contato
- [ ] Clicar no botão flutuante faz scroll suave até #contato
- [ ] Preencher e submeter abre WhatsApp com mensagem personalizada
- [ ] DevTools Network mostra POST para worker_url

**Home Premium:**
- [ ] Form aparece acima do footer
- [ ] Clicar nos CTAs do React faz scroll até o form
- [ ] Submit funciona igual à subpágina

**Sem worker_url:**
- [ ] Form funciona normalmente (abre WhatsApp)
- [ ] Nenhum erro no console (fetch não é chamado)

**Status:** [ ]

---

## Arquivos Afetados

| Arquivo | Ação | Motivo |
|---|---|---|
| `templates/css/style.css` | MODIFY | Remove `.aw-*`, adiciona `.lead-form` |
| `templates/css/widget.css` | NOVO | Form CSS auto-contido (injeção Home Premium) |
| `templates/page.html` | MODIFY | CTA → form, links → #contato |
| `templates/index.html` | MODIFY | CTA → form, links → #contato |
| `templates/js/widget.js` | REWRITE | Interceptor → form handler |
| `core/template_injector.py` | MODIFY | `_inject_leads_form()` |

**Arquivos que NÃO mudam:**
- `core/output_builder.py` — já copia `templates/css/` e `templates/js/`
- `core/site_data_builder.py` — já monta `megaCtaSection` e bloco `leads`
- `cloudflare-worker/index.js` — payload compatível
- `supabase/setup.sql` — schema compatível
- `server.py` — já passa `worker_url` e `client_token`
- `generate.py` — ordem de execução já está correta

---

## Status Geral das Fases

- [x] Fase 1: CSS do formulário
- [x] Fase 2: Templates (page.html + index.html)
- [x] Fase 3: Reescrita widget.js
- [x] Fase 4: Injeção na Home Premium (template_injector.py)
- [ ] Fase 5: Validação visual e E2E
