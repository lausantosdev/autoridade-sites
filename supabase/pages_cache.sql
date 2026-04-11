-- ============================================================
-- Tabela: pages_cache
-- Salva o resultado JSON estruturado da IA para cada página.
-- Permite regenerar os HTMLs rapidamente mudando apenas a configuração
-- (cores, telefone, etc.) sem chamar as APIs do Gemini/OpenAI novamente.
-- Execute no Supabase → SQL Editor
-- ============================================================

create table if not exists public.pages_cache (
    id           uuid        default gen_random_uuid() primary key,
    client_id    uuid        not null references public.clientes_perfil(id) on delete cascade,
    subdomain    text        not null,
    page_slug    text        not null,  -- 'home', 'limpeza-solar-sao-paulo', etc.
    page_type    text        default 'subpage',   -- 'home' ou 'subpage'
    ai_json      jsonb       not null default '{}'::jsonb, -- O flat_result completo da IA
    generated_at timestamptz default now(),
    unique(client_id, page_slug)
);

create index if not exists idx_pages_cache_client_id  on public.pages_cache (client_id);
create index if not exists idx_pages_cache_subdomain  on public.pages_cache (subdomain);

-- RLS: service_role (backend) pode ler/escrever livremente
alter table public.pages_cache enable row level security;
create policy "service all" on public.pages_cache for all using (true) with check (true);
