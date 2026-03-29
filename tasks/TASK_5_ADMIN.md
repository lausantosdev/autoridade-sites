# TASK 5 — Painel Admin (HTML/CSS/JS puro)

## Contexto
Painel exclusivo do dono da agência (você). Enquanto o dashboard do cliente (`dashboard/index.html`) mostra apenas os leads de um token específico, o painel admin mostra **todos os clientes e todos os leads**, usando a `service_role` key do Supabase — que nunca é exposta ao cliente.

O painel é acessado localmente ou em URL protegida por senha básica (HTTP Basic Auth via Cloudflare Access, configurado separadamente). Não há login no HTML — a segurança fica na camada de acesso.

## O que você deve criar

### Arquivo único: `admin/index.html`

HTML, CSS e JS tudo no mesmo arquivo. Mesmo padrão do `dashboard/index.html`.

---

## Configuração (hardcoded — preenchida pelo dono após deploy)

```js
const SUPABASE_URL = 'SUPABASE_URL_AQUI';
const SUPABASE_SERVICE_KEY = 'SUPABASE_SERVICE_KEY_AQUI'; // service_role key
```

> ⚠️ Este arquivo NUNCA deve ser hospedado publicamente. Apenas uso local ou atrás de autenticação (ex: Cloudflare Access).

---

## Query Supabase

Usar Supabase JS v2 via CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```

```js
const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Busca todos os leads, mais recentes primeiro
const { data: leads, error } = await db
  .from('leads')
  .select('*')
  .order('created_at', { ascending: false });
```

A `service_role` key bypassa RLS — retorna todos os leads de todos os clientes.

---

## Schema da tabela `leads` (referência)

```
id           uuid
created_at   timestamptz
client_token text
dominio      text
pagina       text
keyword      text
local        text
nome         text
whatsapp     text
```

---

## Layout e seções

### Header
- Título: "Autoridade Sites — Admin"
- Botão dark mode (igual ao dashboard)

### Cards de resumo globais (linha de 4 cards)
1. **Total de Leads** — count geral
2. **Este Mês** — count do mês atual
3. **Clientes Ativos** — count de `client_token` únicos
4. **Domínios** — count de `dominio` únicos

### Tabela de clientes (visão agrupada)
Título: "Clientes"

Agrupar leads por `client_token`. Para cada grupo:

| Domínio | Client Token | Total Leads | Este Mês | Último Lead | Ação |
|---------|-------------|-------------|----------|-------------|------|

- **Domínio**: pegar `dominio` do lead mais recente do grupo
- **Client Token**: exibir apenas os primeiros 8 caracteres + "..." (ex: `a1b2c3d4...`)
- **Total Leads**: count do grupo
- **Este Mês**: count com `created_at` no mês atual
- **Último Lead**: data do lead mais recente (formato `DD/MM/YYYY`)
- **Ação**: botão "Ver Leads ↓" que expande/colapsa os leads desse cliente inline

### Seção expandível por cliente
Ao clicar em "Ver Leads ↓", exibir abaixo da linha uma tabela inline com os leads daquele cliente:

Colunas: Data | Nome | WhatsApp | Palavra-chave | Local

Mesmo estilo da tabela do `dashboard/index.html`. Clicar novamente colapsa.

### Tabela global de todos os leads
Título: "Todos os Leads (mais recentes)"

Exibir os 100 leads mais recentes de todos os clientes.

Colunas: Data | Domínio | Nome | WhatsApp | Palavra-chave | Local | Token (8 chars)

### Botão de exportação CSV
Acima da tabela global, botão "⬇ Exportar CSV" que gera e baixa um arquivo `leads_export_{data}.csv` com **todos** os leads (não apenas os 100 exibidos).

Campos do CSV: `created_at`, `dominio`, `client_token`, `nome`, `whatsapp`, `keyword`, `local`, `pagina`

```js
function exportCsv(leads) {
    const headers = ['Data', 'Domínio', 'Token', 'Nome', 'WhatsApp', 'Palavra-chave', 'Local', 'Página'];
    const rows = leads.map(l => [
        new Date(l.created_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' }),
        l.dominio, l.client_token, l.nome, l.whatsapp, l.keyword, l.local, l.pagina
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${(v||'').replace(/"/g,'""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }); // BOM para Excel
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leads_export_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}
```

### Footer
"Autoridade Sites — Admin © {ano}" centralizado

---

## Design

Reutilizar exatamente as mesmas CSS variables, fontes e componentes do `dashboard/index.html`:

```css
:root {
    --primary: #2563EB;
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
}

[data-theme="dark"] {
    --primary: #3B82F6;
    --primary-light: #1E3A5F;
    --bg: #0F172A;
    --surface: #1E293B;
    --text: #F1F5F9;
    --text-muted: #94A3B8;
    --border: #334155;
}
```

Dark mode: mesmo padrão do dashboard — toggle manual + `prefers-color-scheme` + `localStorage`.

**Linha expandível do cliente:**
- Fundo levemente diferente (`var(--bg)`) para distinguir da tabela principal
- Animação simples de fade/slide ao expandir (CSS transition em `max-height`)

**Botão "Ver Leads":**
- Estilo outline pequeno, muda para "Fechar ↑" quando expandido

**Responsivo:** Em mobile, tabelas com `overflow-x: auto`.

---

## Segurança (XSS)

Usar a mesma função `escapeHtml` do dashboard para todos os dados vindos do banco:

```js
function escapeHtml(str) {
    if (!str) return '-';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
```

---

## Fluxo JS

```js
async function init() {
    showLoading();
    const leads = await fetchAllLeads();
    hideLoading();

    if (!leads) { showError(); return; }

    renderCards(leads);
    renderClientTable(leads);
    renderGlobalTable(leads);
    showAdmin();
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    init();
    updateFooter();
});
```

---

## O que NÃO fazer
- NÃO usar React, Vue, ou qualquer framework JS
- NÃO criar arquivos separados — tudo em `admin/index.html`
- NÃO expor este arquivo publicamente sem proteção de acesso
- NÃO implementar login/senha no HTML — isso é responsabilidade da camada de hospedagem
- NÃO paginar via API — buscar todos e processar no frontend
- NÃO referenciar arquivos do `dashboard/` — copiar o CSS/JS necessário inline
