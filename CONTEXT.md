# SiteGen — Gerador de Sites SEO para Negócios Locais

> **Produto da [Autoridade Digital](https://autoridade.digital)**
> Gera sites premium, otimizados para SEO e conversão via WhatsApp.

---

## O que é

SiteGen é uma ferramenta que gera automaticamente sites completos para negócios locais brasileiros. O operador preenche os dados do cliente no wizard (nome, nicho, telefone, localidades), clica "Gerar Site", e recebe um ZIP pronto para deploy com:

- **Home page premium** — design dark mode, animações, glassmorphism (template React pré-buildado)
- **Subpáginas SEO** — uma para cada combinação keyword × localidade (~1500 palavras cada)
- **Captura de leads** — formulário WhatsApp com tracking via Cloudflare Worker
- **Dashboard** — painel para o empresário ver seus leads em tempo real

## Stack

| Camada | Tecnologia |
|---|---|
| Pipeline (backend) | Python 3.11 |
| IA (conteúdo) | DeepSeek v3 via OpenRouter |
| IA (imagens) | Google Imagen via Gemini API |
| Template home page | React 19 + Vite + Tailwind v4 (pré-buildado) |
| Template subpáginas | HTML/CSS/JS puros |
| Wizard | FastAPI + WebSocket |
| Leads | Cloudflare Worker + Supabase |
| Dashboard | HTML puro (Supabase client) |

## Estrutura do Projeto

```
sitegen/
├── generate.py              # CLI principal (pipeline)
├── server.py                # Backend do wizard (FastAPI + WebSocket)
├── config.yaml              # Config de exemplo
├── requirements.txt         # Dependências Python
├── .env                     # API keys (OPENROUTER_API_KEY, GEMINI_API_KEY)
│
├── core/                    # Módulos do pipeline
│   ├── config_loader.py     # Parse do config.yaml
│   ├── mixer.py             # Combina keywords × locais
│   ├── sitemap_generator.py # Gera sitemap.xml + mapa-do-site.html
│   ├── topic_generator.py   # Gera tópicos do nicho via IA
│   ├── page_generator.py    # Gera subpáginas SEO via IA
│   ├── site_data_builder.py # Constrói SiteData para a home premium
│   ├── template_injector.py # Injeta dados no template React pré-buildado
│   ├── template_renderer.py # Substitui {{vars}} em templates HTML (shared)
│   ├── imagen_client.py     # Gera hero image via Gemini/Imagen
│   ├── openrouter_client.py # Client OpenRouter (DeepSeek)
│   ├── validator.py         # Valida qualidade das páginas geradas
│   └── utils.py             # Utilitários (hex_to_rgb, slugify, etc.)
│
├── template-dist/           # Template React pré-buildado (NÃO editar)
│   ├── index.html           # HTML com marcadores de injeção
│   └── assets/              # JS/CSS bundled (~134KB gzipped)
│
├── templates/               # Templates HTML puros (subpáginas SEO)
│   ├── index.html           # Home fallback (HTML puro)
│   ├── page.html            # Template das subpáginas
│   ├── css/                 # Estilos
│   ├── js/                  # Scripts
│   └── images/              # Assets estáticos
│
├── frontend/                # UI do wizard
│   └── index.html           # Formulário + WebSocket
│
├── cloudflare-worker/       # Worker de captura de leads
├── dashboard/               # Dashboard de leads (Supabase)
├── supabase/                # Schema SQL do banco
│
├── examples/                # Configs de exemplo (versionadas)
│   └── test_config.yaml     # Configuração de teste (PisoPro)
│
├── tests/                   # Testes unitários (pytest)
│   ├── test_utils.py        # slugify, hex_to_rgb, adjust_color
│   ├── test_mixer.py        # mix_keywords_locations, get_summary
│   └── test_config_loader.py# load_config, get_phone_display, get_whatsapp_link
│
├── Makefile                 # Atalhos: make install, make test, make generate
├── config.example.yaml      # Template de config (sem dados reais)
├── .env.example             # Template de variáveis de ambiente
├── requirements.txt         # Dependências de produção
├── requirements-dev.txt     # Dependências de desenvolvimento (pytest)
│
└── output/                  # Sites gerados (gitignored)
```

## Pipeline (Fluxo de Geração)

```
┌─ Wizard (browser) ──────────────────────────────────┐
│  1. Validar config                                   │
│  2. Gerar mix keywords × locais                      │
│  3. Gerar sitemap.xml + mapa-do-site.html            │
│  4. Gerar hero image (Imagen/Gemini)                 │
│  5. Gerar home page premium (SiteGen template)       │
│  6. Gerar inteligência de negócio (tópicos)          │
│  7. Gerar subpáginas SEO (keyword × local)           │
│  8. Validar qualidade                                │
│  9. Empacotar ZIP                                    │
└──────────────────────────────────────────────────────┘
```

### Home Page — Injeção Híbrida

O template React é buildado **uma única vez** (`npm run build`). O pipeline Python injeta dados dinâmicos sem precisar de Node.js:

```
template-dist/index.html  +  config.yaml + IA
         │                          │
         ▼                          ▼
   HTML com marcadores       site_data_builder.py
   (__SITE_TITLE__, etc.)    (gera SiteData JSON)
         │                          │
         └────────┬─────────────────┘
                  ▼
         template_injector.py
         (substitui marcadores, injeta window.__SITE_DATA__)
                  │
                  ▼
         output/{dominio}/index.html
         (site completo, pronto para deploy)
```

## Como Usar

### Via Wizard (recomendado)
```bash
python server.py
# Abrir http://localhost:8000
# Preencher dados → Gerar Site → Download ZIP
```

### Via CLI
```bash
python generate.py --config config.yaml
# Output em output/{dominio}/
```

### Steps isolados
```bash
python generate.py --step home     # Só home page
python generate.py --step pages    # Só subpáginas SEO
python generate.py --step validate # Só validação
```

### Testes
```bash
make test          # Roda pytest
make test-cov      # Roda com relatório de cobertura
```

## Configuração

### `.env` (API keys)
```
OPENROUTER_API_KEY=sk-or-v1-...
GEMINI_API_KEY=AIzaSy...
```

### `config.yaml` (dados do cliente)
```yaml
empresa:
  nome: "Clean Pro"
  dominio: "cleanpro.com.br"
  categoria: "Limpeza de Estofados"
  telefone_whatsapp: "5541999998888"
  cor_marca: "#2563EB"

seo:
  palavras_chave:
    - Limpeza de Sofá
    - Higienização de Estofados
  locais:
    - Curitiba
    - São José dos Pinhais
```

## Custos por Site

| Item | Custo |
|---|---|
| Conteúdo IA (home + subpáginas) | ~R$0,03 |
| Hero image (Imagen) | Gratuito (free tier) |
| **Total** | **~R$0,03** |

## Rebuild do Template (raro)

Só necessário se o design da home mudar:

```bash
cd [pasta do template React fonte]

# Editar componentes React...

npm run build
# Copiar dist/ para template-dist/
```
