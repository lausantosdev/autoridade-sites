-- ============================================================
-- Tabela: sites_gerados
-- Registra cada site gerado pelo wizard, com link de deploy.
-- Execute no Supabase → SQL Editor
-- ============================================================

create table if not exists public.sites_gerados (
    id           uuid        default gen_random_uuid() primary key,
    subdomain    text        not null,
    empresa_nome text,
    categoria    text,
    telefone     text,
    deploy_url   text,                              -- URL pública (Cloudflare Pages)
    zip_filename text,                              -- nome do arquivo ZIP
    pages        integer     default 0,
    words        integer     default 0,
    cost_usd     numeric(10,6) default 0,
    cost_brl     numeric(10,2) default 0,
    duration     text,
    status       text        default 'zip_only',   -- 'live' ou 'zip_only'
    created_at   timestamptz default now()
);

-- Índice para busca por subdomain e nome
create index if not exists idx_sites_gerados_subdomain    on public.sites_gerados (subdomain);
create index if not exists idx_sites_gerados_created_at   on public.sites_gerados (created_at desc);

-- RLS: service_role (backend) pode inserir; autenticados podem ler
alter table public.sites_gerados enable row level security;

create policy "service insert" on public.sites_gerados
    for insert with check (true);

create policy "authenticated select" on public.sites_gerados
    for select using (auth.role() = 'authenticated');
