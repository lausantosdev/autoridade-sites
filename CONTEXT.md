# Autoridade Sites — Contexto do Projeto

> Leia este arquivo no início de toda sessão de trabalho.
> Leia também `SESSION.md` para saber o que foi feito na última sessão e o que está pendente.

---

## O que é este projeto

**Gerador automatizado de sites SEO local para pequenas empresas brasileiras.**

Dado um `config.yaml` com nome da empresa, palavras-chave e cidades, o sistema gera dezenas de páginas HTML estáticas com conteúdo escrito por IA — prontas para subir em qualquer hospedagem.

O produto completo tem três pilares:

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

O dashboard é o que **fecha a recorrência**: o cliente vê quantos leads vieram e a decisão de continuar pagando fica óbvia.

---

## Genealogia do projeto

```
site_prompts_v9_template_1-mentoria     (Gen 1 — Protótipo manual, OpenAI)
         │
         ▼
    autoridade-sites                    (Gen 2 — Pipeline automatizado, DeepSeek)
         │
         ├── templates/                 (HTML/CSS/JS puro — design Apple-style)
         │
         └── Klema Sites/template       (Gen 3 — Template React de referência)
                 │
                 ├── SiteData interface (contrato de dados tipado)
                 ├── 8 componentes UI   (Hero, Features, FAQ, CTA, etc.)
                 ├── Dark/Light mode    (HSL variables)
                 └── Framer Motion      (micro-animações premium)
```

### O que cada geração trouxe

| Geração | Contribuição principal | Limitação |
|---------|----------------------|-----------|
| **Gen 1** (Mentoria) | Conceito: keywords × locais → páginas SEO | Manual, caro (OpenAI), sem leads |
| **Gen 2** (Autoridade) | Automação total, pipeline modular, leads 24h, custo ~R$1/site | Template HTML básico, sem tipagem |
| **Gen 3** (Klema) | Contrato `SiteData` tipado, design SaaS premium, componentes reutilizáveis | Stack React incompatível com geração estática |

### O que o Klema template **realmente** trouxe (não é só design)

1. **Contrato de dados `SiteData`** — interface TypeScript com 14 seções que formaliza tudo que o pipeline precisa gerar. É a versão tipada do sistema `{{config}}` + `@ia`.
2. **Componentes UI premium** — MagicText (scroll reveal), FAQ com tabs, grid com gap-px, glassmorphism no header.
3. **Theming HSL** — dark/light mode por classe CSS, mais flexível que hex fixo.
4. **IconMapper** — IA retorna nome de ícone como string, template renderiza o componente. No HTML puro, equivale a `fas fa-*` do FontAwesome.

---

## Estratégia de integração (decidida: Híbrida)

O template React (Klema) usa uma stack diferente (React/Vite/Tailwind) da geração estática (HTML puro). A estratégia escolhida é **injeção híbrida em runtime**, que mantém 100% do design sem exigir rebuild por site:

```
┌──────────────────────────────────────────────────────────────────┐
│                    FLUXO DE INTEGRAÇÃO                           │
│                                                                  │
│  [1] BUILD ÚNICO (dev)          [2] POR-SITE (pipeline Python)   │
│  ─────────────────────          ──────────────────────────────   │
│  Klema template                 config.yaml                      │
│       │                              │                           │
│  npm run build                  generate.py (IA gera conteúdo)   │
│       │                              │                           │
│  dist/index.html ◄──────── Python injeta no HTML pré-buildado:   │
│  dist/assets/*.js,css           • <script>window.__SITE_DATA__   │
│                                 • <title>, <meta>, og:tags       │
│                                 • <script type="ld+json">        │
│                                      │                           │
│                                 output/{dominio}/index.html      │
│                                 (design 100% Klema, dados únicos)│
│                                                                  │
│  [3] SUBPÁGINAS SEO (inalterado)                                 │
│  ────────────────────────────                                    │
│  templates/page.html + @placeholders → keyword-local.html        │
│  (continua com HTML puro + CSS Apple-style)                      │
└──────────────────────────────────────────────────────────────────┘
```

### Por que esta estratégia

| Alternativa | Problema |
|------------|---------|
| **CSS Extract** (extrair visual, reescrever HTML puro) | Perde MagicText, Framer Motion, FAQ tabs, dark/light toggle. Semanas de re-trabalho para resultado inferior |
| **Build por site** (Vite build para cada cliente) | Exige Node.js no servidor, ~3s build por site. Desnecessário |
| **Híbrida (escolhida)** ✅ | Uma build serve todos os sites. Python só injeta dados. Design 100%. Sem Node no server |

### O que precisa ser adaptado no Klema template

1. `data.ts` — trocar `export const siteData` por `window.__SITE_DATA__` com fallback para dev
2. `index.html` — manter markers para Python substituir meta tags
3. Pipeline Python — novo step `inject_template.py` que monta o index final

### SEO e a renderização client-side

- **Meta tags, `<title>`, Open Graph, Schema JSON-LD** → injetados pelo Python diretamente no HTML (crawlers leem sem JS)
- **Conteúdo visível** (hero, features, FAQ) → renderizado pelo React em runtime (Googlebot executa JS desde 2019)
- **Subpáginas keyword×local** → continuam 100% HTML estático (zero JS rendering)

---

## Stack técnica

| Camada | Tecnologia |
|--------|-----------|
| Pipeline de geração | Python 3 + ThreadPoolExecutor (30 workers) |
| API de IA | OpenRouter → DeepSeek V3.2 (padrão) + Gemini (disponível) |
| Geração de imagens | `core/imagen_client.py` |
| Interface web | FastAPI + WebSocket (progresso em tempo real) |
| Templates de saída | HTML/CSS/JS puro (sem framework) |
| Lead capture | Cloudflare Worker (proxy seguro) + Supabase (banco) |
| Dashboard do cliente | HTML estático + Supabase anon key + RLS |
| Painel admin | `admin/index.html` (spec em `tasks/TASK_5_ADMIN.md`) |
| Template de referência | React/Vite/Tailwind (somente design — `Klema Sites/template`) |

---

## Pipeline de geração (`generate.py`)

```
config.yaml → mixer → sitemap → topics (cache) → pages (paralelo, IA) → validator → report
```

1. `config_loader.py` — carrega YAML, aceita CSV do Google Keyword Planner
2. `mixer.py` — produto cartesiano keywords × locais → lista de páginas com slug
3. `sitemap_generator.py` — gera sitemap.xml + mapa-do-site.html
4. `topic_generator.py` — gera 100 palavras + 100 frases do nicho via IA (cache em `cache/`)
5. `page_generator.py` — preenche template com conteúdo IA (paralelo)
6. `validator.py` — checa placeholders órfãos, contagem de palavras, H1/H2, links internos

---

## Sistema de placeholders

O pipeline usa dois tipos de placeholder que são resolvidos em momentos diferentes:

| Tipo | Sintaxe | Quando resolve | Fonte | Exemplo |
|------|---------|---------------|-------|---------| 
| Config | `{{variavel}}` | Antes da geração (igual em todas as páginas) | config.yaml | `{{empresa_nome}}`, `{{cor_marca}}` |
| IA | `@placeholder` | Durante a geração (único por página) | DeepSeek/Gemini via OpenRouter | `@titulo`, `@faq_1_resposta` |

`@context` e `@type` no JSON-LD não são placeholders — o validator ignora blocos `<script>`.

### Mapeamento com o contrato Klema `SiteData`

| `SiteData` (Klema) | Placeholder (Autoridade) | Fonte |
|--------------------|------------------------|-------|
| `empresa.nome` | `{{empresa_nome}}` | config.yaml |
| `theme.color` | `{{cor_marca}}` | config.yaml |
| `hero.titleLine1` | `@hero_titulo_linha_1` | IA |
| `faqSection.faqs[0].question` | `@faq_1_pergunta` | IA |
| `links.whatsappPagina` | `@whatsapp_pagina` | Pipeline (gerado) |
| `schema.localBusiness` | `{{schema_markup}}` | Pipeline (gerado) |

---

## Estrutura de conteúdo (Estratégia Iceberg)

Cada página SEO segue esta estrutura de alta conversão:

```
1. Hero          — Título 3 linhas + CTA WhatsApp (conversão imediata)
2. Trust Bar     — 3 ícones de credibilidade (sem números inventados)
3. Dor           — Problema do cliente (copy emocional)
4. Benefícios    — 4 cards com ícone + título + texto (visual + SEO)
5. Processo      — Como funciona (SEO técnico heavy, 120-150 palavras/bloco)
6. Autoridade    — Sobre a empresa (credibilidade + SEO semântico)
7. FAQ           — 3 perguntas (Schema FAQPage + voice search)
8. CTA Final     — Bloco colorido com WhatsApp
9. Mapa          — Google Maps embed (dark mode filter)
10. Footer       — 4 colunas: Sobre / Contato / Serviços / Cidades
```

---

## Fluxo de leads

```
[Site do cliente — HTML público]
      ↓ POST { nome, whatsapp, dominio, pagina, keyword, local }
[Cloudflare Worker] ← SUPABASE_SERVICE_KEY fica aqui, nunca no HTML
      ↓ valida client_token
[Supabase — tabela leads]
      ↓
[Dashboard — HTML estático com anon key + RLS por client_token]
```

`client_token` é um UUID por cliente. Não é login — é isolamento de dados via RLS.

---

## Status das features

| Feature | Status | Arquivo principal |
|---------|--------|------------------|
| Pipeline CLI | ✅ Pronto | `generate.py` |
| Wizard web (FastAPI + WebSocket) | ✅ Pronto | `server.py` |
| Templates HTML/CSS/JS | ✅ Pronto | `templates/` |
| Schema markup (LocalBusiness + FAQPage) | ✅ Pronto | `templates/page.html` |
| Design Apple-style (CSS) | ✅ Integrado | `templates/css/style.css` |
| Widget de captura de leads | ✅ Pronto | `templates/js/widget.js` |
| Cloudflare Worker | ✅ Pronto | `cloudflare-worker/index.js` |
| Supabase setup | ✅ Pronto | `supabase/setup.sql` |
| Dashboard do cliente | ✅ Pronto | `dashboard/index.html` |
| Geração de imagens (imagen_client) | ✅ Integrado | `core/imagen_client.py` |
| Gemini como modelo alternativo | ✅ Integrado | `server.py` + `models.json` |
| Template Klema de referência | ✅ Completo | `Klema Sites/template` (externo) |
| Integração híbrida Klema → index.html | ⏳ Pendente | `data.ts` → `window.__SITE_DATA__` + `inject_template.py` |
| Painel Admin | ⏳ Pendente | spec: `tasks/TASK_5_ADMIN.md` |
| Deploy automático (Cloudflare Pages) | ⏳ Pendente | — |
| Multi-tenant no wizard | ⏳ Futuro | — |

---

## Infraestrutura manual pendente

Estas etapas precisam ser feitas uma vez por cliente (ou por ambiente):

1. Criar projeto Supabase → executar `supabase/setup.sql`
2. Deploy Cloudflare Worker → `cd cloudflare-worker && wrangler deploy`
3. Configurar secrets do Worker: `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`
4. Preencher `config.yaml`: `leads.worker_url` e `leads.client_token`
5. Hospedar `dashboard/` (Cloudflare Pages ou GitHub Pages)

---

## Comandos frequentes

```bash
python generate.py                    # pipeline completo
python generate.py --step pages       # só gerar páginas
python generate.py --force-topics     # regenerar cache de tópicos
python generate.py --config outro.yaml
python server.py                      # wizard web em localhost:8000
```

---

## Decisões de arquitetura não óbvias

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Output format | HTML estático | Hospedagem grátis, SEO nativo, zero runtime |
| Modelo IA | DeepSeek V3.2 via OpenRouter | 2.3x mais barato que V3, qualidade superior |
| Template React | Só referência, não integrado | Incompatível com geração estática multi-page |
| Leads backend | Cloudflare Worker + Supabase | Grátis (100k req/dia), seguro (key no Worker) |
| Cache de tópicos | `cache/` local | Evita regerar frases do nicho a cada run |
| CSS variables | `{{cor_marca}}` substituída na geração | Theming sem JS — CSS puro |
| Validação | Regex no validator.py | Simples, detecta placeholders órfãos |
| Estratégia SEO | Iceberg (copy no topo, SEO heavy embaixo) | Conversão + ranqueamento no mesmo page |

---

## Regras de roteamento de tarefas

| Situação | Estratégia |
|----------|-----------|
| Arquivo novo, lógica isolada, spec clara | Agente barato — criar `tasks/TASK_N.md` primeiro |
| Arquivo novo, lógica complexa | Claude direto |
| Modificar arquivo existente | Claude direto — ler o arquivo antes |
| Volume alto de arquivos similares | Agente barato |

**Formato da spec para agente barato:** contexto em 3-5 linhas + caminhos exatos + schema + pseudocódigo + "O que NÃO fazer".

---

## Referência: Contrato SiteData (resumo do Klema)

O template Klema (`Klema Sites/template/src/data.ts`) define a interface mestre que o pipeline deve produzir. Seções principais:

```
empresa     { nome, dominio, categoria, telefones, horario, endereco, ano }
theme       { mode: "dark"|"light", color: hex, colorRgb }
links       { whatsapp, whatsappPagina, telefone, googleMapsEmbed }
seo         { title, metaDescription, metaKeywords, og*, keyword, local }
hero        { badgeText, titleLine1, titleLine2, subtitle, heroImagePath }
features    { title, subtitle, items[]: { title, iconName, description } }
authority   { eyebrow, title, manifestoText }
megaCta     { title, subtitle }
faq         { title, subtitle, categories, faqs: Record<cat, Q&A[]> }
map         { eyebrow, title, embedUrl }
footer      { descricao, servicos[], cidades[], credito }
nav         { links[]: { label, href } }
schema      { localBusiness: JSON-LD, faqPage: JSON-LD }
leads       { workerUrl, clientToken }
```

Consulte o arquivo original para detalhes: `c:\Users\ThinkPad T480\Desktop\Klema\Klema Sites\template\src\data.ts`
