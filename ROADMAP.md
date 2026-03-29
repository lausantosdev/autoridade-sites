# Autoridade Sites — Roadmap e Visão do Produto

## O que é este projeto

Gerador automatizado de sites SEO para negócios locais brasileiros. A partir de um config com nome da empresa, palavras-chave e locais, gera dezenas de páginas otimizadas para o Google usando IA (DeepSeek via OpenRouter), com interface web (FastAPI + WebSocket) e CLI.

**Repositório:** `c:\Users\ThinkPad T480\autoridade-sites\`
**Baseado em:** projeto do Tiago (`site_prompts_v9_template_1-mentoria`)
**Stack:** Python + FastAPI + DeepSeek + HTML/CSS/JS puro

---

## O que já foi construído (sessões anteriores)

### Pipeline de geração
- Geração de páginas SEO em paralelo (workers configuráveis)
- Mix automático de palavras-chave × locais
- Geração de tópicos do nicho com cache
- Sitemap XML + mapa do site HTML
- Validador de qualidade com relatório

### SEO técnico
- **Schema Markup** injetado em cada página: `LocalBusiness` + `FAQPage`
- **WhatsApp personalizado por página**: mensagem pré-preenchida com keyword + local
  Ex: `"Olá, quero saber sobre Pizza Artesanal em Pinheiros"`
- **Footer rico** com 4 colunas: Sobre / Contato / Serviços / Cidades Atendidas
  (gerado automaticamente do config — sem custo de IA)
- Campo `endereco` opcional no config (reforça NAP para SEO local)

### Interface
- Wizard web (FastAPI) com WebSocket para progresso em tempo real
- Progresso por página (não polling — fila assíncrona)
- Custo exibido em USD e BRL
- Campo de upload de CSV (Google Keyword Planner / Ubersuggest)

### Qualidade
- Validador corrigido: ignora blocos `<script>` ao checar placeholders
  (evitava falso positivo com `@context` / `@type` do Schema Markup)
- H1 do `index.html` simplificado: `empresa_nome` + `empresa_categoria`

---

## Visão do Produto — O que falta construir

### Proposta de valor para o cliente final

```
┌─────────────────────────────────────────────────┐
│           AUTORIDADE SITES (produto)             │
├─────────────────┬───────────────┬────────────────┤
│  1. SEO Pages   │  2. Widget    │  3. Dashboard  │
│                 │     24h       │    do Cliente  │
│  Páginas que    │  Captura lead │  Vê os leads,  │
│  ranqueiam no   │  qualquer     │  decide se     │
│  Google         │  hora         │  continua      │
└─────────────────┴───────────────┴────────────────┘
```

O dashboard é o que **fecha a recorrência**: o cliente vê quantos leads vieram do sistema e a decisão de continuar pagando se torna óbvia.

---

## Fase 1 — Widget de Captura + Backend de Leads

### O widget (template HTML/JS)

- Aparece **24 horas** quando o visitante clica no botão de WhatsApp
- Roda uma conversa simulada: nome → WhatsApp → confirmação
- Ao final: abre WhatsApp com mensagem estruturada + salva lead no banco

**Mensagem gerada no WhatsApp:**
```
Olá! Me chamo João Silva.
WhatsApp: (11) 99999-8888
Interesse: Pizza Artesanal em Pinheiros
```

**Variação por horário (opcional/futuro):**
- Dentro do horário: abre WhatsApp direto (sem fricção)
- Fora do horário: abre o widget de captura

### Stack decidida

| Componente | Tecnologia | Custo |
|-----------|-----------|-------|
| Widget | HTML/CSS/JS puro (embutido no template) | Grátis |
| Endpoint receptor | **Cloudflare Worker** | Grátis (100k req/dia) |
| Banco de leads | **Supabase** | Grátis até ~50k leads/mês |

### Por que Cloudflare Worker (não expor chave do Supabase no HTML)

```
[Site do cliente — HTML público]
        ↓ POST { nome, whatsapp, dominio, pagina, keyword, local }
[Cloudflare Worker] ← chave do Supabase fica AQUI, segura
        ↓
[Supabase — tabela leads]
```

### Schema da tabela `leads` no Supabase

```sql
CREATE TABLE leads (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at  timestamptz DEFAULT now(),
  client_token text NOT NULL,   -- token único por cliente
  dominio     text,             -- ex: petclean.com.br
  pagina      text,             -- URL da página onde capturou
  keyword     text,             -- ex: Banho para Cachorro
  local       text,             -- ex: Vila Mariana
  nome        text,
  whatsapp    text
);
```

### Config necessário no autoridade-sites

Adicionar ao `config.yaml` e wizard:
```yaml
leads:
  worker_url: "https://leads.SEU-SUBDOMINIO.workers.dev"
  client_token: "uuid-unico-por-cliente"
```

### Arquivos a criar/modificar

| Arquivo | O que fazer |
|---------|------------|
| `templates/js/widget.js` | Lógica do chat widget (novo arquivo) |
| `templates/index.html` | Incluir widget |
| `templates/page.html` | Incluir widget |
| `templates/css/style.css` | Estilos do widget |
| `core/page_generator.py` | Injetar `worker_url` e `client_token` |
| `config.yaml` | Adicionar seção `leads` |
| `server.py` | Campos `worker_url` e `client_token` no wizard |
| `cloudflare-worker/index.js` | Worker que recebe e salva no Supabase (novo) |

---

## Fase 2 — Dashboard do Cliente

### Como funciona

O cliente acessa uma URL única:
```
app.autoridade-sites.com.br/dashboard?token=SEU-TOKEN
```

**O que vê:**
- Total de leads do mês atual
- Leads por página/keyword (ranking)
- Lista completa: data, nome, WhatsApp, página de origem
- Histórico mês a mês

### Stack

- HTML/CSS/JS puro (sem framework)
- Supabase JS client com anon key + Row Level Security
- RLS: cada token só acessa seus próprios leads
- Hospedagem: Cloudflare Pages ou GitHub Pages (grátis)

### Row Level Security (Supabase)

```sql
-- Política: cliente só vê seus próprios leads
CREATE POLICY "client sees own leads"
ON leads FOR SELECT
USING (client_token = current_setting('app.client_token', true));
```

---

## Fase 3 — Painel Admin (você)

- Vê todos os clientes e todos os leads
- Métricas gerais por cliente
- Exporta relatório PDF mensal por cliente
- Gestão de tokens (criar novo cliente, revogar acesso)

---

## Decisões técnicas tomadas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Banco de leads | Supabase | Gratuito, dashboard, RLS, escala |
| Endpoint intermediário | Cloudflare Worker | Protege credenciais, grátis, zero manutenção |
| Widget | JS puro embutido no template | Zero dependência externa, zero setup por cliente |
| Dashboard | HTML estático + Supabase anon key + RLS | Simples, seguro, sem backend |
| Captação | 24h (não só fora do horário) | Mais leads, sem complexidade de lógica de horário |
| Dados capturados | nome + whatsapp + pagina + keyword + local | Suficiente para provar ROI ao cliente |

---

## Próxima sessão — por onde começar

1. Criar projeto no Supabase e a tabela `leads`
2. Criar o Cloudflare Worker (`cloudflare-worker/index.js`)
3. Implementar o widget (`templates/js/widget.js` + estilos)
4. Integrar widget nos templates (`index.html` e `page.html`)
5. Adicionar campos `worker_url` e `client_token` ao config e wizard
6. Testar end-to-end com empresa fictícia

---

## Estado atual do repositório

**Branch:** `main`
**Último commit:** `c42b082` — fix validator ignorar blocos script

**Commits desta sessão:**
- `4a4ab4f` — WhatsApp personalizado por página
- `54973a8` — Footer rico (serviços, cidades, endereço)
- `7ae152d` — H1 simplificado no index
- `c42b082` — Validator corrigido (falso positivo JSON-LD)
- `1402a22` — .gitignore ignorar .claude/
- `3799244` — .gitignore server_log.txt
- `774b888` — Schema Markup + progresso real-time + custo BRL
