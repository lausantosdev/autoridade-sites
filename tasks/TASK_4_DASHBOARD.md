# TASK 4 — Dashboard do Cliente (HTML/CSS/JS puro)

## Contexto
Cada cliente do Autoridade Sites tem um `client_token` (UUID único). O dashboard permite que o cliente veja seus leads capturados pelo widget de WhatsApp, acessando uma URL com seu token:

```
https://app.autoridade-sites.com.br/dashboard/?token=UUID-DO-CLIENTE
```

O banco é Supabase. O dashboard lê com a **anon key** (segura para frontend) e filtra por `client_token` na query.

## O que você deve criar

### Arquivo único: `dashboard/index.html`

HTML, CSS e JS **tudo no mesmo arquivo** (sem arquivos externos além do Supabase JS CDN).

---

## Configuração (hardcoded no HTML — será preenchida após deploy do Supabase)

```js
const SUPABASE_URL = 'SUPABASE_URL_AQUI';
const SUPABASE_ANON_KEY = 'SUPABASE_ANON_KEY_AQUI';
```

Deixe essas duas constantes como placeholders — o dono do projeto vai preencher depois.

---

## Comportamento geral

1. Ao carregar, ler `?token=` da URL
2. Se token ausente ou vazio → mostrar tela de erro: "Token inválido. Acesse o link enviado pela Autoridade Sites."
3. Se token presente → buscar leads do Supabase e renderizar dashboard

---

## Query Supabase

Usar Supabase JS v2 via CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```

```js
const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const { data: leads, error } = await db
  .from('leads')
  .select('*')
  .eq('client_token', token)
  .order('created_at', { ascending: false });
```

Se `error` → mostrar mensagem de erro genérica (não expor detalhes técnicos).
Se `leads` vazio → mostrar estado vazio com mensagem amigável.

---

## Schema da tabela `leads` (para referência)

```
id           uuid
created_at   timestamptz
client_token text
dominio      text       -- ex: petclean.com.br
pagina       text       -- URL completa da página de origem
keyword      text       -- ex: Banho para Cachorro
local        text       -- ex: Vila Mariana
nome         text       -- nome capturado pelo widget
whatsapp     text       -- whatsapp capturado pelo widget
```

---

## Layout e seções

### Header
- Logo/título: "Autoridade Sites" à esquerda
- Subtítulo: "Dashboard de Leads — {dominio}" (pegar dominio do primeiro lead)
- Se não há leads, subtítulo: "Dashboard de Leads"

### Cards de resumo (linha de 3 cards)
1. **Total de Leads** — count de todos os leads do token
2. **Este Mês** — count de leads com `created_at` no mês atual
3. **Esta Semana** — count de leads com `created_at` nos últimos 7 dias

### Ranking de Páginas (tabela simples)
Título: "Leads por Palavra-chave"
Agrupar leads por `keyword`, ordenar por count desc.
Colunas: Palavra-chave | Quantidade | Barra visual (div com largura proporcional ao max)

### Tabela completa de leads
Título: "Todos os Leads"
Colunas: Data | Nome | WhatsApp | Palavra-chave | Local

- Data: formatar como `DD/MM/YYYY HH:mm` no timezone Brasil (use `toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'})`)
- WhatsApp: exibir como texto simples (não link — privacidade)
- Ordenação: mais recente primeiro (já vem ordenado da query)
- Se mais de 50 leads, mostrar só os 50 mais recentes com nota "Exibindo os 50 leads mais recentes"

### Footer
"Autoridade Sites © {ano}" centralizado

---

## Design

HTML/CSS puro, sem framework. Paleta:

```css
--primary: #2563EB;       /* azul */
--primary-light: #EFF6FF;
--bg: #F8FAFC;
--surface: #FFFFFF;
--text: #1E293B;
--text-muted: #64748B;
--border: #E2E8F0;
--success: #10B981;
--radius: 12px;
--shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
--shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07);
```

Fonte: `Inter` via Google Fonts (adicionar no `<head>`).

**Cards de resumo:**
- background: white, border-radius: var(--radius), box-shadow, padding 24px
- Número grande (2rem, font-weight 700, color: var(--primary))
- Label abaixo (text-muted, 0.875rem)

**Tabelas:**
- thead: background var(--bg), font-weight 600, font-size 0.8rem uppercase, color text-muted
- tbody tr: border-bottom 1px solid var(--border), hover background var(--primary-light)
- cells: padding 12px 16px

**Barra visual do ranking:**
```html
<div style="background: var(--primary); height: 6px; border-radius: 3px; width: {pct}%"></div>
```

**Responsivo:** Em mobile (< 640px), os 3 cards ficam em coluna. A tabela completa permite scroll horizontal (`overflow-x: auto`).

**Loading state:** Enquanto busca dados, mostrar um spinner simples (CSS animation) no centro da tela.

**Estado vazio:** Se nenhum lead encontrado, mostrar ícone 📭 + texto "Nenhum lead capturado ainda. Os leads aparecerão aqui assim que visitantes interagirem com o widget de WhatsApp."

---

## Estrutura HTML sugerida

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard — Autoridade Sites</title>
  <!-- Google Fonts Inter -->
  <!-- Supabase JS CDN -->
  <style>/* todo o CSS aqui */</style>
</head>
<body>
  <div id="app">
    <!-- Loading inicial -->
    <div id="loading">...</div>
    <!-- Erro -->
    <div id="error" style="display:none">...</div>
    <!-- Dashboard -->
    <div id="dashboard" style="display:none">
      <header>...</header>
      <main>
        <section id="cards">...</section>
        <section id="ranking">...</section>
        <section id="leads-table">...</section>
      </main>
      <footer>...</footer>
    </div>
  </div>
  <script>/* todo o JS aqui */</script>
</body>
</html>
```

---

## Fluxo JS (pseudocódigo)

```js
async function init() {
  const token = new URLSearchParams(window.location.search).get('token');
  if (!token) { showError(); return; }

  showLoading();
  const leads = await fetchLeads(token);
  hideLoading();

  if (!leads) { showError(); return; }

  renderCards(leads);
  renderRanking(leads);
  renderTable(leads);
  showDashboard();
}

document.addEventListener('DOMContentLoaded', init);
```

---

## O que NÃO fazer
- NÃO usar React, Vue, ou qualquer framework JS
- NÃO criar arquivos CSS ou JS separados — tudo no `dashboard/index.html`
- NÃO expor a `service_role` key — usar apenas `anon key`
- NÃO adicionar autenticação por senha — o token na URL é a "senha"
- NÃO paginar os dados via API — buscar todos e filtrar no frontend (volume baixo)
- NÃO criar backend — dashboard é 100% estático
