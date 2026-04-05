# SPEC — Sessão 2 (04/04/2026): Alinhamento da Home Premium (React) com UX de Leads

> **Atividade:** Captura de Leads — Home Premium
> **Plano associado:** `PLAN_CAPTURA_LEADS_04_04_2026.md`
> **Pré-requisito:** Sessão 1 (Subpáginas) concluída e commitada (`a0bb9bf`)

---

## Contexto Crítico

A Home Premium é gerada por um template **React pré-buildado** em `template-dist/`.
Não existe `frontend/src/` — o source React **não faz parte do repo**. O bundle minificado
(`template-dist/assets/index-BYtPjAsq.js`, 388KB) renderiza as seções da Home a partir de
`window.__SITE_DATA__`, injetado pelo `core/template_injector.py`.

**O que já funciona (Sessão 1):**
- Subpáginas (`page.html`) têm formulário "Fale Conosco" perfeito com CSS `:valid` e validação JS
- `widget.css` + `widget.js` estão completos e testados
- `template_injector.py` já injeta `<section id="contato">` + `widget.js` + `AUTORIDADE_WIDGET` na Home

**Problemas identificados na Home Premium (PetVida `localhost:8080`):**

| # | Problema | Root Cause | Evidência |
|---|---------|------------|-----------|
| H-01 | **Seção CTA duplicada:** React renderiza sua própria MegaCTA (botão wa.me) + injector adiciona formulário #contato | O bundle React tem uma seção `megaCtaSection` hardcoded que renderiza `<a href=X.links.whatsapp>` com `X.whatsappCtaText` | Screenshot desktop: 2 CTAs visíveis |
| H-02 | **Formulário posicionado DEPOIS do footer** | `_inject_leads_form()` insere antes de `</body>`, mas o footer é renderizado pelo React dentro de `#root` — o form fica fora do `#root` | Screenshot mobile: form flutuando após footer |
| H-03 | **Título "Agende uma consulta agora!"** na seção injetada | `megaCtaSection.title` do `site_data` diz "Agende..." — o `template_injector` usa esse valor literalmente | Deveria ser "Fale Conosco" como nas subpáginas |
| H-04 | **Seção #contato sem estilos de container** porque está fora do contexto CSS do React | As classes `.cta-section`, `.container`, `.cta-title`, `.cta-subtitle` são definidas no CSS do template React ou no `style.css` (que a Home Premium não carrega) | Card do form aparece sem background de seção |

---

## Estratégia de Solução

> **Restrição fundamental:** Não temos acesso ao source React. Não podemos fazer `npm run build`.
> Toda modificação na Home é feita via:
> 1. **Injeção Python** (`template_injector.py`) — HTML/CSS/JS inserido no `index.html` gerado
> 2. **Pós-processamento JS** (scripts injetados que rodam após React renderizar o DOM)

### Abordagem escolhida: **Substituir a MegaCTA do React pelo formulário via pós-processamento JS**

Em vez de ter 2 CTAs, vamos:
1. Deixar o React renderizar sua MegaCTA normalmente (ela fica **dentro** do `#root`, antes do footer)
2. Via JS pós-React, **esvaziar o conteúdo** da MegaCTA e **mover** o formulário injetado para dentro dela
3. Isso resolve H-01 (duplicação), H-02 (posição) e H-04 (contexto CSS) de uma vez

---

## Sumário de Fases

- [x] Fase 1: Corrigir título megaCTA no `site_data_builder.py`
- [x] Fase 2: Reescrever `_inject_leads_form()` no `template_injector.py`
- [x] Fase 3: Regenerar site PetVida e validar visualmente
- [x] Fase 4: Teste E2E (desktop + mobile)

---

## Fase 1 — Corrigir título megaCTA no `site_data_builder.py`

### Problema
O campo `megaCtaSection.title` é gerado pela IA e pode conter texto de venda pressivo como
"Agende uma consulta agora!". Nas subpáginas, já trocamos para "Fale Conosco".
A Home precisa do mesmo tratamento.

### Solução

**Arquivo:** `core/site_data_builder.py`

Localizar onde `megaCtaSection` é montado e **substituir** o título/subtítulo por valores fixos
consistentes com a comunicação aprovada:

```python
# Forçar comunicação genérica na seção CTA (alinhado com subpáginas)
site_data['megaCtaSection'] = {
    'title': 'Fale Conosco',
    'subtitle': 'Tire suas dúvidas ou solicite mais informações conversando com nossa equipe pelo WhatsApp.'
}
```

> **Nota:** Isso substitui os valores gerados pela IA. A decisão é intencional — a seção CTA
> não deve ter copy de venda pressiva, conforme aprovado na Sessão 8.

### Checkpoint Fase 1
- Confirmar que `site_data_builder.py` seta `megaCtaSection.title = 'Fale Conosco'`
- Testes existentes não devem quebrar:
```bash
python -m pytest tests/ --cov=core --cov-fail-under=75
```

---

## Fase 2 — Reescrever `_inject_leads_form()` no `template_injector.py`

### Problema Atual
A função atual (linhas 224-295) injeta:
1. `<link>` para `widget.css` no `<head>` ✅ (correto, manter)
2. `<section id="contato">` com formulário HTML antes de `</body>` ❌ (fica fora do `#root`)
3. `<script>` com `AUTORIDADE_WIDGET` + `widget.js` ❌ (posição ok, mas depende do form estar no lugar certo)

### Solução

Reescrever `_inject_leads_form()` para:

1. **Manter** a injeção do CSS link (`widget.css`) no `<head>` 
2. **Manter** a injeção do HTML do formulário `<section id="contato">` antes de `</body>` (como HTML oculto/staging area)
3. **Manter** a configuração `AUTORIDADE_WIDGET` e `widget.js`
4. **Adicionar** CSS inline que oculta inicialmente a seção injetada: `#contato { display: none; }`
5. **Adicionar** estilos de container inline para a seção `#contato` (já que `.cta-section` e `.container` não existem no CSS do React)
6. **Adicionar** um novo script `leads-home-integrator` que:
   - Espera o React renderizar o DOM (via `setTimeout` ou `MutationObserver`)
   - Localiza a seção MegaCTA do React (identificável pelo texto de `megaCtaSection.title` ou pelo padrão de classes)
   - Esvazia o conteúdo interno da MegaCTA
   - Move o `<section id="contato">` para dentro da MegaCTA
   - Remove o `display: none` do `#contato`
   - O formulário herda o posicionamento correto (antes do footer, dentro do `#root`)

### Estrutura do script integrador

```js
// leads-home-integrator.js (injetado inline)
(function() {
  function integrateForm() {
    // 1. Encontrar o form injetado
    var form = document.getElementById('contato');
    if (!form) return false;

    // 2. Encontrar a MegaCTA do React
    // A MegaCTA renderiza megaCtaSection.title dentro de um <h2> com classes específicas
    // Padrão: section > div contendo h2 com o texto do título
    var sections = document.querySelectorAll('#root section');
    var megaCta = null;
    
    sections.forEach(function(sec) {
      var h2 = sec.querySelector('h2');
      if (h2 && sec.querySelector('a[href*="wa.me"]')) {
        // Seção que tem um h2 E um link wa.me é a MegaCTA
        megaCta = sec;
      }
    });

    if (!megaCta) return false;

    // 3. Substituir conteúdo da MegaCTA pelo formulário
    // Preservar a section do React (com suas classes e posição no DOM)
    // Limpar o conteúdo interno
    var innerContainer = megaCta.querySelector(':scope > div');
    if (innerContainer) {
      innerContainer.innerHTML = '';
      // Mover o conteúdo do form (não a section externa) para dentro
      innerContainer.appendChild(form.querySelector('.container') || form);
    }

    // 4. Mostrar o form (remover display:none)
    form.style.display = '';
    
    // 5. Remover a section staging (fora do #root) se ficou vazia  
    if (form.parentNode && form.parentNode !== innerContainer) {
      form.parentNode.removeChild(form);
    }

    return true;
  }

  // Executar após React renderizar
  function tryIntegrate() {
    if (!integrateForm()) {
      // React ainda não renderizou — tentar novamente
      setTimeout(tryIntegrate, 200);
    }
  }

  if (document.readyState === 'complete') {
    setTimeout(tryIntegrate, 300);
  } else {
    window.addEventListener('load', function() {
      setTimeout(tryIntegrate, 300);
    });
  }
})();
```

### CSS de Container Inline (para quando .cta-section não existe)

Adicionar no `<style>` injetado (ou inline no `#contato`):

```css
/* Container styles for injected contact section */
#contato {
  display: none; /* Oculto até o integrador posicionar */
}
#contato .container {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 24px;
  text-align: center;
}
#contato .cta-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--foreground, #0f172a);
}
#contato .cta-subtitle {
  font-size: 0.95rem;
  color: var(--muted-foreground, #64748b);
  margin-bottom: 32px;
  line-height: 1.6;
}
/* Dark theme */
[data-theme="dark"] #contato .cta-title {
  color: var(--foreground, #e2e8f0);
}
```

### Checkpoint Fase 2
- `template_injector.py` alterado com a nova `_inject_leads_form()`
- Testes existentes passam:
```bash
python -m pytest tests/ --cov=core --cov-fail-under=75
```

---

## Fase 3 — Regenerar site PetVida e validar visualmente

### 3.1 — Parar o servidor HTTP atual (porta 8080 ocupada)

### 3.2 — Regenerar o site PetVida do zero
```bash
python generate.py --config config-test.yaml
```

### 3.3 — Servir novamente
```bash
cd output/petvida.test
python -m http.server 8080
```

### 3.4 — Abrir no browser e verificar visualmente

**Desktop (`localhost:8080/index.html`):**
- [ ] A seção MegaCTA do React agora contém o formulário (não mais o botão wa.me)
- [ ] Título é "Fale Conosco" (não "Agende uma consulta agora!")
- [ ] Subtítulo é genérico e suave
- [ ] Formulário aparece ANTES do footer (dentro do fluxo normal)
- [ ] Apenas 1 CTA visível (sem duplicação)
- [ ] Card do formulário com visual consistente (white card, botão cinza→verde)

**Mobile (viewport 400px):**
- [ ] Formulário não transborda lateralmente
- [ ] Campos empilham verticalmente
- [ ] Botão ocupa largura total do card

### Checkpoint Fase 3
- Screenshot desktop e mobile confirmando layout correto

---

## Fase 4 — Teste E2E (desktop + mobile)

### 4.1 — Funcionalidade do formulário na Home
- [ ] Preencher Nome + WhatsApp → botão fica verde
- [ ] Submeter → abre WhatsApp com mensagem pré-preenchida
- [ ] Mensagem contém nome digitado + keyword + local
- [ ] Form reseta após 2s
- [ ] Botão fica "Abrindo WhatsApp..." durante loading

### 4.2 — Smooth scroll dos CTAs do React
- [ ] Clicar "Fale Conosco" no navbar → scroll suave até o formulário
- [ ] Clicar "Fale Conosco" no hero → scroll suave até o formulário
- [ ] Botão flutuante WhatsApp → scroll suave até o formulário
- [ ] `widget.js` MutationObserver intercepta links `wa.me` dinâmicos do React

### 4.3 — Validação UX
- [ ] Submeter vazio → erro visual (shake + borda vermelha + mensagem contextual)
- [ ] WhatsApp inválido (menos de 8 dígitos) → erro específico
- [ ] Apenas nome preenchido → botão NÃO fica verde (CSS `:valid` requer ambos)

### 4.4 — Subpáginas (regressão)
- [ ] Abrir uma subpágina (ex: `veterinario-sao-paulo.html`)  
- [ ] Confirmar que o formulário das subpáginas continua funcionando normalmente
- [ ] O script integrador NÃO interfere (não há MegaCTA react nas subpáginas)

### 4.5 — Sem erros
- [ ] Console do browser sem erros JS
- [ ] Nenhum request 404

### Checkpoint Fase 4
> ✅ Todos os itens acima marcados como OK

---

## Arquivos Modificados

| Arquivo | Ação | Motivo |
|---|---|---|
| `core/site_data_builder.py` | MODIFY | Forçar `megaCtaSection.title` = "Fale Conosco" |
| `core/template_injector.py` | MODIFY | Reescrever `_inject_leads_form()` com script integrador |

**Arquivos que NÃO mudam:**
- `templates/css/widget.css` — já está correto
- `templates/js/widget.js` — já está correto (MutationObserver + form handler)
- `templates/page.html` — subpáginas já estão OK
- `templates/index.html` — home fallback já está OK
- `template-dist/` — NÃO tocamos no bundle React

---

## Ordem de Execução

```
Fase 1 (site_data_builder) → Fase 2 (template_injector) → Fase 3 (Regen + Visual) → Fase 4 (E2E)
```

**Regra:** Não avançar para a próxima fase sem o checkpoint anterior passar.
