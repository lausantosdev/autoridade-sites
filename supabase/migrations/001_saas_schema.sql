-- ============================================================
-- SiteGen Cloud — Migration 001: SaaS Schema
-- Executar no Supabase SQL Editor
-- ORDEM IMPORTA: executar bloco a bloco, sem pular
-- ============================================================

-- ── BLOCO 1: Enum de status de job ───────────────────────────
-- Usar text CHECK em vez de enum Postgres para facilitar futuras
-- adições de status sem necessidade de nova migration de tipo.

-- ── BLOCO 2: Tabela clientes_perfil ──────────────────────────
CREATE TABLE IF NOT EXISTS clientes_perfil (
  id              uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at      timestamptz DEFAULT now() NOT NULL,
  agency_id       uuid        REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  client_token    text        UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,

  -- Identidade do cliente
  empresa_nome    text        NOT NULL,
  subdomain       text        NOT NULL UNIQUE
                              CHECK (subdomain ~ '^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$'),
  custom_domain   text        DEFAULT NULL,

  -- Configuração do site
  categoria       text        NOT NULL DEFAULT '',
  cor_marca       text        NOT NULL DEFAULT '#2563EB'
                              CHECK (cor_marca ~ '^#[0-9A-Fa-f]{6}$'),
  servicos        text[]      NOT NULL DEFAULT '{}',
  telefone        text        NOT NULL DEFAULT '',
  endereco        text        NOT NULL DEFAULT '',
  google_maps_url text        DEFAULT NULL,
  horario         text        NOT NULL DEFAULT 'Segunda a Sexta, 8h às 18h',
  keywords        text[]      NOT NULL DEFAULT '{}',
  locais          text[]      NOT NULL DEFAULT '{}',
  theme_mode      text        NOT NULL DEFAULT 'auto'
                              CHECK (theme_mode IN ('auto', 'dark', 'light')),
  max_workers     integer     NOT NULL DEFAULT 30
                              CHECK (max_workers BETWEEN 1 AND 50),

  -- Estado do deploy
  status          text        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'generating', 'live', 'error')),
  last_generated  timestamptz DEFAULT NULL,

  -- URL pública resolvida automaticamente:
  -- usa custom_domain se existir, senão monta <subdomain>.autoridade.digital
  site_url        text GENERATED ALWAYS AS (
    CASE
      WHEN custom_domain IS NOT NULL THEN 'https://' || custom_domain
      ELSE 'https://' || subdomain || '.autoridade.digital'
    END
  ) STORED
);

-- ── BLOCO 3: Tabela jobs ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
  id              uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at      timestamptz DEFAULT now() NOT NULL,
  agency_id       uuid        REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  client_id       uuid        REFERENCES clientes_perfil(id) ON DELETE SET NULL,

  -- Controle de estado
  status          text        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'generating', 'deploying', 'complete', 'failed')),
  step            text        NOT NULL DEFAULT 'queue'
                              CHECK (step IN ('queue','validating','mixing','sitemap','hero',
                                              'home_data','topics','home_page','subpages',
                                              'validating_quality','packaging','deploying','done')),
  progress_pct    integer     NOT NULL DEFAULT 0
                              CHECK (progress_pct BETWEEN 0 AND 100),

  -- Timestamps
  started_at      timestamptz DEFAULT NULL,
  finished_at     timestamptz DEFAULT NULL,

  -- Logs estruturados: array de objetos {ts, level, message}
  -- Usar jsonb para permitir filtragem: logs @> '[{"level":"error"}]'
  logs            jsonb       NOT NULL DEFAULT '[]'::jsonb,

  -- Erro final (se status = 'failed')
  error_message   text        DEFAULT NULL
);

-- ── BLOCO 4: Tabela historico_geracao ─────────────────────────
CREATE TABLE IF NOT EXISTS historico_geracao (
  id                    uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at            timestamptz DEFAULT now() NOT NULL,
  job_id                uuid        REFERENCES jobs(id) ON DELETE SET NULL,
  client_id             uuid        REFERENCES clientes_perfil(id) ON DELETE SET NULL,
  agency_id             uuid        REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

  -- Métricas da geração
  total_pages_generated integer     NOT NULL DEFAULT 0,
  valid_pages           integer     NOT NULL DEFAULT 0,
  error_pages           integer     NOT NULL DEFAULT 0,
  duration_seconds      integer     NOT NULL DEFAULT 0,

  -- Custo: NUNCA usar float para dinheiro — usar numeric(10,6)
  cost_usd              numeric(10,6) NOT NULL DEFAULT 0,
  cost_brl              numeric(10,4) NOT NULL DEFAULT 0,
  tokens_used           integer     NOT NULL DEFAULT 0,

  -- Provedores utilizados
  gemini_tokens         integer     NOT NULL DEFAULT 0,
  openai_tokens         integer     NOT NULL DEFAULT 0
);

-- ── BLOCO 5: Migração/Criação da tabela leads ───────────────
-- Cria a tabela caso você esteja usando um Projeto Limpo/Novo no Supabase
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

-- O Worker usa service_role key que BYPASSA RLS no INSERT —
-- Adiciona o vinculo da agência:
ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS agency_id uuid REFERENCES auth.users(id) ON DELETE SET NULL;

-- ── BLOCO 6: Índices ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS clientes_perfil_agency_idx ON clientes_perfil (agency_id);
CREATE INDEX IF NOT EXISTS clientes_perfil_subdomain_idx ON clientes_perfil (subdomain);
CREATE INDEX IF NOT EXISTS jobs_agency_idx ON jobs (agency_id);
CREATE INDEX IF NOT EXISTS jobs_client_idx ON jobs (client_id);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
CREATE INDEX IF NOT EXISTS historico_agency_idx ON historico_geracao (agency_id);
CREATE INDEX IF NOT EXISTS leads_agency_idx ON leads (agency_id);

-- ── BLOCO 7: Row Level Security ───────────────────────────────
-- OBRIGATÓRIO desde o Dia 1. Multi-tenancy real.

ALTER TABLE clientes_perfil ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_geracao ENABLE ROW LEVEL SECURITY;
-- leads já tem RLS habilitado (setup.sql anterior)

-- Policies: agência vê apenas seus próprios dados
CREATE POLICY "agency_own_clientes"
ON clientes_perfil FOR ALL
TO authenticated
USING (agency_id = auth.uid())
WITH CHECK (agency_id = auth.uid());

CREATE POLICY "agency_own_jobs"
ON jobs FOR ALL
TO authenticated
USING (agency_id = auth.uid())
WITH CHECK (agency_id = auth.uid());

CREATE POLICY "agency_own_historico"
ON historico_geracao FOR ALL
TO authenticated
USING (agency_id = auth.uid())
WITH CHECK (agency_id = auth.uid());

-- Leads: o Worker usa service_role (bypassa RLS no INSERT automaticamente).
-- Para SELECT no dashboard, a agência filtra pelos seus clientes.
-- Remover a policy anon existente e criar policy authenticated:
DROP POLICY IF EXISTS "anon_select_leads" ON leads;

CREATE POLICY "agency_select_leads"
ON leads FOR SELECT
TO authenticated
USING (
  client_token IN (
    SELECT client_token FROM clientes_perfil WHERE agency_id = auth.uid()
  )
);

-- Append atômico ao logs jsonb para evitar race condition
CREATE OR REPLACE FUNCTION append_job_log(job_id uuid, log_entry jsonb)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE jobs
  SET logs = logs || jsonb_build_array(log_entry)
  WHERE id = job_id;
$$;
