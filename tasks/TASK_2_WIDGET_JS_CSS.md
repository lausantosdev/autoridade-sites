# TASK 2 — Widget de Captura de Leads (JS + CSS)

## Contexto
Sites SEO estáticos para pequenas empresas brasileiras. Cada site tem botões de WhatsApp (`a[href*="wa.me"]`). O widget deve interceptar esses cliques, abrir uma conversa simulada para capturar nome + WhatsApp do visitante, salvar no backend, e então abrir o WhatsApp.

## Configuração disponível via `window.AUTORIDADE_WIDGET`

O objeto `window.AUTORIDADE_WIDGET` **já estará injetado no HTML** antes do widget.js carregar (isso será feito por outra tarefa). O widget deve apenas ler esse objeto:

```js
window.AUTORIDADE_WIDGET = {
  workerUrl: "https://autoridade-leads.SEU-SUBDOMINIO.workers.dev",
  clientToken: "uuid-unico-do-cliente",
  dominio: "petclean.com.br",
  empresaNome: "Pet Clean",
  whatsappNumero: "5511999998888",   // formato internacional sem +
  keyword: "Banho para Cachorro",    // pode ser "" na página inicial
  local: "Vila Mariana"              // pode ser "" na página inicial
}
```

**Se `window.AUTORIDADE_WIDGET` não existir ou `workerUrl` estiver vazio, o widget não deve fazer nada** (botões WhatsApp funcionam normalmente).

## O que você deve criar

### Arquivo 1: `templates/js/widget.js`

**Comportamento:**

1. Ao carregar (`DOMContentLoaded`), interceptar cliques em todos os elementos `a[href*="wa.me"]`
2. Ao clicar: prevenir comportamento padrão, guardar a URL de destino do WhatsApp, abrir o modal do widget
3. O modal exibe uma conversa sequencial em 3 etapas:

**Etapa 1 — Mensagem inicial + campo nome:**
```
Bot: "Olá! 👋 Para te atender melhor no WhatsApp, pode me dizer seu nome?"
[Input: "Seu nome completo"]   [Botão: "Continuar →"]
```

**Etapa 2 — Campo WhatsApp:**
```
Bot: "Perfeito, {nome}! Qual é o seu WhatsApp para retorno?"
[Input: "Ex: (11) 99999-8888"]   [Botão: "Ir para WhatsApp →"]
```

**Etapa 3 — Após envio (sem esperar resposta da API):**
- Fechar modal imediatamente
- Abrir WhatsApp (a URL guardada no passo 2) em nova aba
- Disparar o POST para o worker em background (fire-and-forget com `.catch(() => {})`)

**POST para o worker:**
```js
fetch(window.AUTORIDADE_WIDGET.workerUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nome: nomeCaptado,
    whatsapp: whatsappCaptado,
    dominio: window.AUTORIDADE_WIDGET.dominio,
    pagina: window.location.href,
    keyword: window.AUTORIDADE_WIDGET.keyword,
    local: window.AUTORIDADE_WIDGET.local,
    client_token: window.AUTORIDADE_WIDGET.clientToken
  })
}).catch(() => {});
```

**Validação mínima:**
- Nome: não pode ser vazio
- WhatsApp: mínimo 8 dígitos numéricos (extrair só dígitos para validar, mas salvar como o usuário digitou)

**UX:**
- Pressionar Enter avança para próxima etapa
- Botão "×" no canto superior direito fecha o modal (sem ir para WhatsApp)
- Modal tem overlay escuro de fundo (clique no overlay fecha o modal sem ir para WhatsApp)
- Auto-focus no input de cada etapa

**Estrutura HTML do modal (injetada via JS no `document.body`):**
```html
<div id="aw-overlay" class="aw-overlay">
  <div id="aw-modal" class="aw-modal">
    <button id="aw-close" class="aw-close" aria-label="Fechar">×</button>
    <div class="aw-header">
      <div class="aw-avatar"><i class="fab fa-whatsapp"></i></div>
      <div>
        <div class="aw-title">{empresaNome}</div>
        <div class="aw-status">● Online agora</div>
      </div>
    </div>
    <div id="aw-messages" class="aw-messages"></div>
    <div id="aw-input-area" class="aw-input-area">
      <input id="aw-input" class="aw-input" type="text" />
      <button id="aw-send" class="aw-send">Continuar →</button>
    </div>
  </div>
</div>
```

**Importante:**
- Usar JS puro (sem jQuery, sem frameworks)
- Não poluir o namespace global — usar IIFE ou bloco `{ }` para variáveis internas
- Exportar apenas a função de inicialização se necessário

### Arquivo 2: APPEND ao final de `templates/css/style.css`

**Adicionar ao FINAL do arquivo** (não substituir nenhum conteúdo existente) os estilos do widget.

CSS variables disponíveis (já definidas no arquivo): `--primary`, `--primary-rgb`, `--bg`, `--bg-alt`, `--text`, `--text-muted`, `--border`, `--radius`, `--radius-lg`, `--shadow-xl`, `--transition`, `--font`

Os estilos devem:
- `.aw-overlay`: position fixed, inset 0, background rgba(0,0,0,0.5), z-index 9999, display flex, align-items center, justify-content center. Quando hidden: display none
- `.aw-modal`: background var(--bg), border-radius var(--radius-lg), width min(420px, 92vw), max-height 85vh, overflow hidden, box-shadow var(--shadow-xl), display flex, flex-direction column
- `.aw-header`: background var(--primary), color white, padding 16px 20px, display flex, gap 12px, align-items center
- `.aw-avatar`: background rgba(255,255,255,0.2), width 44px, height 44px, border-radius 50%, display flex, align-items center, justify-content center. O `i` dentro: font-size 1.4rem
- `.aw-title`: font-weight 600, font-size 1rem
- `.aw-status`: font-size 0.75rem, opacity 0.85
- `.aw-close`: position absolute, top 12px, right 16px, background none, border none, color white, font-size 1.5rem, cursor pointer, line-height 1, opacity 0.8. Hover: opacity 1
- `.aw-messages`: flex 1, overflow-y auto, padding 20px, display flex, flex-direction column, gap 12px
- `.aw-bubble`: background var(--bg-alt), border-radius var(--radius), padding 12px 16px, font-size 0.9rem, line-height 1.5, max-width 85%, border 1px solid var(--border)
- `.aw-input-area`: padding 16px 20px, border-top 1px solid var(--border), display flex, gap 8px
- `.aw-input`: flex 1, padding 10px 14px, border 1.5px solid var(--border), border-radius var(--radius), font-family var(--font), font-size 0.9rem, outline none. Focus: border-color var(--primary)
- `.aw-send`: background var(--primary), color white, border none, border-radius var(--radius), padding 10px 18px, font-weight 600, cursor pointer, font-size 0.85rem, white-space nowrap, transition var(--transition). Hover: opacity 0.9. Disabled: opacity 0.5, cursor not-allowed

Adicionar também `position: relative` ao `.aw-modal` (necessário para o botão close com position absolute).

## O que NÃO fazer
- NÃO modificar `index.html` ou `page.html` (isso será feito separadamente)
- NÃO modificar `main.js` ou `dados.js`
- NÃO adicionar `window.AUTORIDADE_WIDGET = ...` no widget.js (isso virá do HTML)
- NÃO substituir conteúdo existente do style.css — apenas APPEND no final
- NÃO usar bibliotecas externas
