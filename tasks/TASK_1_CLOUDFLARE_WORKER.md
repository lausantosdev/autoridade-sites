# TASK 1 — Cloudflare Worker: Endpoint Receptor de Leads

## Contexto
Este projeto gera sites SEO estáticos para pequenas empresas brasileiras. Os sites precisam capturar leads (nome + WhatsApp do visitante) e salvar em um banco Supabase. Como o site é estático (HTML puro), não podemos expor a service key do Supabase no código frontend. A solução é um Cloudflare Worker como intermediário seguro.

## O que você deve criar

### Arquivo 1: `cloudflare-worker/index.js`

O Worker deve:
1. Responder a requisições `OPTIONS` com headers CORS corretos (preflight)
2. Responder a requisições `POST` com o corpo JSON do lead
3. Validar campos obrigatórios
4. Inserir o lead na tabela Supabase via REST API
5. Retornar JSON de sucesso ou erro

**Campos recebidos no POST (todos string):**
```json
{
  "nome": "João Silva",
  "whatsapp": "11999998888",
  "dominio": "petclean.com.br",
  "pagina": "https://petclean.com.br/banho-cachorro-vila-mariana.html",
  "keyword": "Banho para Cachorro",
  "local": "Vila Mariana",
  "client_token": "uuid-unico-do-cliente"
}
```

**Campos obrigatórios:** `nome`, `whatsapp`, `client_token`

**Inserção Supabase via REST:**
- URL: `${SUPABASE_URL}/rest/v1/leads`
- Method: POST
- Headers:
  - `apikey: ${SUPABASE_SERVICE_KEY}`
  - `Authorization: Bearer ${SUPABASE_SERVICE_KEY}`
  - `Content-Type: application/json`
  - `Prefer: return=minimal`

**Variáveis de ambiente do Worker (via `env`):**
- `env.SUPABASE_URL` — ex: `https://xyzxyz.supabase.co`
- `env.SUPABASE_SERVICE_KEY` — a service_role key do Supabase

**Headers CORS a incluir em TODA resposta:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

**Respostas esperadas:**
- Sucesso: HTTP 200, `{ "ok": true }`
- Campo obrigatório faltando: HTTP 400, `{ "ok": false, "error": "Campo obrigatório ausente: {campo}" }`
- Método não permitido: HTTP 405, `{ "ok": false, "error": "Método não permitido" }`
- Erro de inserção Supabase: HTTP 500, `{ "ok": false, "error": "Erro ao salvar lead" }`

**Use a sintaxe moderna de Cloudflare Workers (export default, sem addEventListener):**
```js
export default {
  async fetch(request, env, ctx) { ... }
}
```

### Arquivo 2: `cloudflare-worker/wrangler.toml`

Arquivo de configuração mínimo para deploy com Wrangler CLI:
```toml
name = "autoridade-leads"
main = "index.js"
compatibility_date = "2024-01-01"

[vars]
# Defina as variáveis reais via: wrangler secret put SUPABASE_URL
# wrangler secret put SUPABASE_SERVICE_KEY
```

### Arquivo 3: `cloudflare-worker/README.md`

Instruções curtas de deploy (máximo 30 linhas):
1. Pré-requisitos: Node.js, conta Cloudflare
2. `npm install -g wrangler && wrangler login`
3. `cd cloudflare-worker && wrangler deploy`
4. Configurar secrets: `wrangler secret put SUPABASE_URL` e `wrangler secret put SUPABASE_SERVICE_KEY`
5. Copiar a URL do Worker gerada para usar no `config.yaml` do projeto

## O que NÃO fazer
- NÃO modificar nenhum outro arquivo do projeto
- NÃO criar testes
- NÃO adicionar dependências npm (Workers rodam sem node_modules)
- NÃO usar `addEventListener` (estilo antigo) — use `export default`

## Schema da tabela `leads` no Supabase (para referência)
```sql
CREATE TABLE leads (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at  timestamptz DEFAULT now(),
  client_token text NOT NULL,
  dominio     text,
  pagina      text,
  keyword     text,
  local       text,
  nome        text,
  whatsapp    text
);
```
