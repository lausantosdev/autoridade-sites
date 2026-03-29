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

## Fase 1 — Widget de Captura + Backend de Leads ✅ Concluída

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

## Fase 2 — Dashboard do Cliente ✅ Concluída

**Arquivo:** `dashboard/index.html`

- Cards: total de leads / este mês / esta semana
- Ranking de leads por palavra-chave com barra visual
- Tabela completa com timezone BR (limite 50 registros)
- Dark mode: toggle manual + respeita `prefers-color-scheme`
- Proteção XSS em todos os dados do usuário
- Hospedagem: Cloudflare Pages ou GitHub Pages (grátis)

---

## Fase 3 — Painel Admin ⏳ Aguardando execução

**Spec:** `tasks/TASK_5_ADMIN.md`
**Arquivo a criar:** `admin/index.html`

- Cards globais: total leads / mês / clientes ativos / domínios
- Tabela de clientes com expandir/colapsar leads inline
- Tabela global dos 100 leads mais recentes
- Exportação CSV (todos os leads)
- Exportação PDF (relatório mensal por cliente, via jsPDF)

---

## Infraestrutura pendente (ações manuais)

1. Criar projeto Supabase → executar `supabase/setup.sql`
2. Deploy Cloudflare Worker → `cd cloudflare-worker && wrangler deploy`
3. Configurar secrets do Worker: `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`
4. Preencher `config.yaml`: `leads.worker_url` e `leads.client_token`
5. Hospedar `dashboard/` (Cloudflare Pages ou GitHub Pages)

---

## Decisões técnicas tomadas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Banco de leads | Supabase | Gratuito, RLS, escala |
| Endpoint intermediário | Cloudflare Worker | Protege credenciais, grátis, zero manutenção |
| Widget | JS puro embutido no template | Zero dependência externa, zero setup por cliente |
| Dashboard | HTML estático + Supabase anon key + RLS | Simples, seguro, sem backend |
| Captação | 24h contínuo | Mais leads, sem lógica de horário |
| Dados capturados | nome + whatsapp + pagina + keyword + local | Suficiente para provar ROI ao cliente |
| Modelo IA | DeepSeek V3.2 via OpenRouter | Melhor qualidade, 2.3x mais barato no output que V3 |

---

## Estado atual do repositório

**Branch:** `main`
**Último commit:** `ad675b6` — atualiza CLAUDE.md com roteamento de agentes

**Commits relevantes:**
- Widget + CSS + integração pipeline
- Cloudflare Worker (index.js, wrangler.toml)
- Dashboard com dark mode e proteção XSS
- Migração para DeepSeek V3.2
- Tasks 1–5 (specs para agentes)
