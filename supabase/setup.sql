-- ============================================================
-- Autoridade Sites — Supabase Setup
-- Execute no SQL Editor do painel Supabase
-- ============================================================

-- 1. Tabela de leads
CREATE TABLE IF NOT EXISTS leads (
  id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at   timestamptz DEFAULT now(),
  client_token text NOT NULL,
  dominio      text,
  pagina       text,
  keyword      text,
  local        text,
  nome         text,
  whatsapp     text
);

-- 2. Índices para consultas do dashboard
CREATE INDEX IF NOT EXISTS leads_client_token_idx ON leads (client_token);
CREATE INDEX IF NOT EXISTS leads_created_at_idx   ON leads (created_at DESC);

-- 3. Habilitar Row Level Security
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- 4. Política: Worker (service key) pode inserir livremente
--    A service key bypassa RLS automaticamente — nenhuma policy necessária para INSERT.

-- 5. Política: anon key pode ler leads (dashboard filtra por client_token na query)
--    Segurança baseada em UUID unguessable — mesmo modelo de "secret links".
CREATE POLICY "anon_select_leads"
ON leads FOR SELECT
TO anon
USING (true);

-- ============================================================
-- Após executar, copie:
--   - Project URL  → SUPABASE_URL no Cloudflare Worker
--   - service_role key → SUPABASE_SERVICE_KEY no Cloudflare Worker
--   - anon key → workerUrl no dashboard (leitura pública segura)
-- ============================================================
