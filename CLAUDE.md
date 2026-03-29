# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |

---

# Autoridade Sites — Contexto do Projeto

Gerador de sites SEO local para pequenas empresas brasileiras. Dado um config.yaml com empresa + palavras-chave + cidades, gera N páginas HTML estáticas com conteúdo IA, prontas para subir em qualquer hospedagem.

## Pipeline (generate.py)

```
config.yaml → mixer → sitemap → topics (cache) → pages (paralelo, IA) → validator → report
```

1. `config_loader.py` — carrega e valida YAML, aceita CSV do Google Keyword Planner
2. `mixer.py` — produto cartesiano keywords × locais → lista de páginas com slug/filename
3. `sitemap_generator.py` — gera sitemap.xml + mapa-do-site.html
4. `topic_generator.py` — gera 100 palavras + 100 frases do nicho via IA; salva em `cache/`
5. `page_generator.py` — preenche template com conteúdo IA (ThreadPoolExecutor, max_workers=30)
6. `validator.py` — checa placeholders órfãos, contagem de palavras, H1/H2, links internos

## Sistema de placeholders (dois tipos)

| Tipo | Sintaxe | Fonte | Exemplo |
|------|---------|-------|---------|
| Config | `{{variavel}}` | config.yaml | `{{empresa_nome}}`, `{{cor_marca}}` |
| IA | `@placeholder` | DeepSeek via OpenRouter | `@titulo`, `@faq_1_resposta` |

**Atenção:** `@context` e `@type` no JSON-LD schema não são placeholders — o validator ignora blocos `<script>` por isso.

## Comandos frequentes

```bash
python generate.py                    # pipeline completo
python generate.py --step pages       # só gerar páginas
python generate.py --force-topics     # regenerar cache de tópicos
python generate.py --config outro.yaml
python server.py                      # wizard web em localhost:8000
```

## Saída

```
output/{dominio}/
├── index.html
├── mapa-do-site.html
├── {keyword}-{local}.html  (60+ páginas)
├── sitemap.xml
├── css/, js/
└── reports/{dominio}_report.md
```

## API

- Provider: OpenRouter (`OPENROUTER_API_KEY` no `.env`)
- Modelo padrão: `deepseek/deepseek-chat`
- Custo típico: ~R$1,00 por site de 60 páginas

## Status das features

| Feature | Status |
|---------|--------|
| Gerador CLI + Web (FastAPI/WebSocket) | ✅ Pronto |
| Templates HTML/CSS/JS | ✅ Pronto |
| Schema markup (LocalBusiness + FAQPage) | ✅ Pronto |
| Widget de captura de leads (JS puro) | ⏳ Planejado |
| Cloudflare Worker (endpoint seguro para leads) | ⏳ Planejado |
| Supabase (armazenamento de leads + RLS) | ⏳ Planejado |
| Dashboard do cliente (token-based) | ⏳ Planejado |

## Decisões de arquitetura não óbvias

- **Cache de tópicos** (`cache/`): evita regerar frases do nicho a cada run; o mesmo cache serve todas as páginas do mesmo cliente.
- **Cloudflare Worker como proxy**: sites são estáticos — não dá expor a service key do Supabase no HTML. O Worker valida o `client_token` antes de inserir leads.
- **`client_token`** por cliente: permite RLS no Supabase sem criar usuário por cliente; cada token é um UUID fixo no config.
- **CSS variables no style.css**: `{{cor_marca}}` e `{{cor_marca_rgb}}` são substituídas na geração, não em runtime — CSS puro, sem JS para theming.
