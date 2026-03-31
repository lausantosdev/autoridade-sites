# SESSION.md — Log de Sessões de Trabalho

> Leia este arquivo junto com `CONTEXT.md` no início de toda sessão.
> Ao fim de cada sessão, atualize a seção "Última Sessão" com o que foi feito.
> Mova o conteúdo anterior para "Histórico".

---

## Última Sessão — 2026-03-29

### O que foi feito

**1. Design Apple-style integrado (`templates/css/style.css`)**
- Refatoração visual completa do CSS: tipografia, espaçamentos, sombras e contraste revisados
- Correções de contraste em texto sobre fundos coloridos (acessibilidade)
- Estilo mais limpo e moderno, inspirado no Klema template (React) mas mantendo HTML puro

**2. Gemini adicionado como modelo alternativo (`server.py` + `models.json`)**
- `models.json` criado com lista de modelos disponíveis via OpenRouter (DeepSeek, Gemini, etc.)
- Wizard web agora permite selecionar o modelo antes de gerar

**3. Geração de imagens integrada (`core/imagen_client.py`)**
- Novo cliente para geração de imagens via IA (arquivo novo)
- Integrado ao `generate.py`

**4. Arquivo de mock para testes (`tmp_mock_generate.py`)**
- Script temporário para simular geração sem consumir créditos de API
- Útil para testar o wizard e o output visual

**5. Análise técnica dos 3 projetos no workspace**
- Comparação: `site_prompts_v9` (original) vs `autoridade-sites` (produção) vs `Klema template` (React/UI)
- Conclusão: o Klema template tem design excelente mas stack incompatível (React + Vite vs HTML estático)
- Decisão: extrair o visual do Klema e reescrever como HTML/CSS puro (não integrar React)

### Decisões tomadas

- Manter output como HTML estático (não adotar React/Vite na pipeline de geração)
- `models.json` como fonte de verdade para modelos disponíveis (fácil de atualizar sem mexer em código)
- Design Apple-style via CSS puro (sem dependências externas)

### O que ficou pendente

- [ ] **Painel Admin** (`admin/index.html`) — spec em `tasks/TASK_5_ADMIN.md`, candidato a agente barato
- [ ] **Deploy automático** — integração com Cloudflare Pages API para publicar o site gerado direto do wizard
- [ ] **Migração do visual Klema** — extrair componentes do React e reescrever como HTML/CSS puro no template
- [ ] **Infraestrutura real** — Supabase + Cloudflare Worker ainda não deployados em produção
- [ ] **Multi-tenant no wizard** — server.py atual serve um job por vez; falta fila + isolamento por cliente

---

## Como atualizar este arquivo

Ao fim de cada sessão, substitua "Última Sessão" com o novo conteúdo e mova o anterior para "Histórico" abaixo.

**Template para nova sessão:**

```
## Última Sessão — YYYY-MM-DD

### O que foi feito
- Item 1
- Item 2

### Decisões tomadas
- Decisão e motivo

### O que ficou pendente
- [ ] Tarefa A
- [ ] Tarefa B
```

---

## Histórico

*(sessões anteriores serão movidas aqui)*

### 2026-03-28 — Dashboard + Supabase + Cloudflare Worker
- Dashboard do cliente com dark mode, ranking de leads, proteção XSS
- Setup SQL do Supabase (`supabase/setup.sql`)
- Cloudflare Worker como proxy seguro para o banco

### 2026-03-27 — Widget de captura de leads
- Widget JS puro embutido nos templates
- Chat simulado: nome → whatsapp → confirmação → WhatsApp pré-preenchido + salva lead
- Integração com `config.yaml` (worker_url, client_token)

### Antes disso — Pipeline core
- Pipeline completo: mixer → sitemap → topics → pages → validator → report
- Migração OpenAI → DeepSeek V3.2 via OpenRouter (~R$1/site de 60 páginas)
- Wizard web FastAPI + WebSocket para progresso em tempo real
