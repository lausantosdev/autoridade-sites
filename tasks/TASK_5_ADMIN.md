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

#### Exportação PDF (Relatório Mensal por Cliente)

Adicionar jsPDF via CDN no `<head>`:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
```

Ao clicar em "⬇ Relatório PDF", gerar um PDF com **uma página por cliente**, contendo:

**Cabeçalho de cada página:**
```
AUTORIDADE SITES — Relatório Mensal
Cliente: petclean.com.br
Período: Abril/2025
Token: a1b2c3d4...
```

**Resumo do cliente:**
```
Total de leads no mês: 12
Total geral: 47
```

**Tabela de leads do mês atual do cliente:**
Colunas: Data | Nome | WhatsApp | Palavra-chave | Local

**Rodapé de cada página:**
```
Gerado em DD/MM/YYYY — Autoridade Sites
```

**Implementação com jsPDF:**
```js
function exportPdf(leads) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    const now = new Date();
    const mesAtual = new Date(now.getFullYear(), now.getMonth(), 1);
    const nomeMes = now.toLocaleString('pt-BR', { month: 'long', year: 'numeric' });

    // Agrupar por client_token
    const clientes = {};
    leads.forEach(l => {
        if (!clientes[l.client_token]) clientes[l.client_token] = [];
        clientes[l.client_token].push(l);
    });

    let primeiraPage = true;

    Object.entries(clientes).forEach(([token, clientLeads]) => {
        if (!primeiraPage) doc.addPage();
        primeiraPage = false;

        const dominio = clientLeads[0]?.dominio || 'desconhecido';
        const leadsDoMes = clientLeads.filter(l => new Date(l.created_at) >= mesAtual);
        const tokenCurto = token.slice(0, 8) + '...';

        let y = 20;

        // Cabeçalho
        doc.setFontSize(16);
        doc.setFont(undefined, 'bold');
        doc.text('AUTORIDADE SITES — Relatório Mensal', 14, y);
        y += 10;

        doc.setFontSize(11);
        doc.setFont(undefined, 'normal');
        doc.text(`Cliente: ${dominio}`, 14, y); y += 7;
        doc.text(`Período: ${nomeMes}`, 14, y); y += 7;
        doc.text(`Token: ${tokenCurto}`, 14, y); y += 12;

        // Resumo
        doc.setFont(undefined, 'bold');
        doc.text(`Leads no mês: ${leadsDoMes.length}`, 14, y); y += 7;
        doc.text(`Total geral: ${clientLeads.length}`, 14, y); y += 12;

        // Tabela de leads do mês
        if (leadsDoMes.length === 0) {
            doc.setFont(undefined, 'italic');
            doc.text('Nenhum lead capturado neste mês.', 14, y);
        } else {
            doc.setFont(undefined, 'bold');
            doc.setFontSize(9);
            doc.text('Data', 14, y);
            doc.text('Nome', 45, y);
            doc.text('WhatsApp', 95, y);
            doc.text('Palavra-chave', 130, y);
            doc.text('Local', 175, y);
            y += 6;

            doc.setFont(undefined, 'normal');
            leadsDoMes.forEach(lead => {
                if (y > 270) { doc.addPage(); y = 20; }
                const data = new Date(lead.created_at).toLocaleString('pt-BR', {
                    timeZone: 'America/Sao_Paulo', day:'2-digit', month:'2-digit', year:'numeric'
                });
                doc.text(data,                          14, y);
                doc.text((lead.nome || '-').slice(0,20), 45, y);
                doc.text((lead.whatsapp || '-').slice(0,18), 95, y);
                doc.text((lead.keyword || '-').slice(0,22), 130, y);
                doc.text((lead.local || '-').slice(0,16), 175, y);
                y += 6;
            });
        }

        // Rodapé
        doc.setFontSize(8);
        doc.setTextColor(150);
        doc.text(
            `Gerado em ${new Date().toLocaleDateString('pt-BR')} — Autoridade Sites`,
            14, 285
        );
        doc.setTextColor(0);
    });

    const nomeArquivo = `relatorio_${now.toISOString().slice(0,7)}.pdf`;
    doc.save(nomeArquivo);
}
```

### Tabela global de todos os leads
Título: "Todos os Leads (mais recentes)"

Exibir os 100 leads mais recentes de todos os clientes.

Colunas: Data | Domínio | Nome | WhatsApp | Palavra-chave | Local | Token (8 chars)

### Botões de exportação
Acima da tabela global, dois botões lado a lado:
- "⬇ Exportar CSV" — exporta todos os leads em CSV
- "⬇ Relatório PDF" — gera relatório mensal por cliente em PDF

#### Exportação CSV
Baixa `leads_export_{data}.csv` com **todos** os leads (não apenas os 100 exibidos).

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
