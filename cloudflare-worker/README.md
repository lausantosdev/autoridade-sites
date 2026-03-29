# Cloudflare Worker: Endpoint Receptor de Leads

Este Worker recebe leads dos sites estáticos e os salva no Supabase.

## Pré-requisitos
- Node.js instalado
- Conta Cloudflare
- Wrangler CLI instalado (`npm install -g wrangler`)

## Configuração
1. Faça login na Cloudflare:
   ```bash
   wrangler login
   ```

2. Navegue até o diretório do Worker:
   ```bash
   cd cloudflare-worker
   ```

3. Configure as variáveis de ambiente (secrets):
   ```bash
   wrangler secret put SUPABASE_URL
   wrangler secret put SUPABASE_SERVICE_KEY
   ```

4. Implante o Worker:
   ```bash
   wrangler deploy
   ```

5. Copie a URL gerada e use-a no `config.yaml` do projeto principal.

## Notas
- O Worker valida campos obrigatórios (`nome`, `whatsapp`, `client_token`).
- Responde a requisições `OPTIONS` para CORS.
- Apenas métodos `POST` são permitidos.