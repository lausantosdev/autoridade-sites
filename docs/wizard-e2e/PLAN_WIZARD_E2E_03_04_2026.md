# Finalização de Produto: Wizard Web E2E

> **Sprint:** Finalização de Produto (atividade 1 de 3)
> **Sessão:** 1 — 03/04/2026
> **Spec associada:** `SPEC_SESSAO1_03_04_2026.md` (nesta mesma pasta)
> **Objetivo:** Corrigir bugs, adicionar validações, integrar campos de leads e testar o Wizard de ponta a ponta.

## Contexto

O Wizard Web (`server.py` + `frontend/index.html`) está funcional mas com bugs de sincronização, validações ausentes e sem campos de integração de leads. Esta atividade resolve tudo isso e valida com teste real.

## Diagnóstico (Brainstorm)

### 🔴 Bugs encontrados

1. **Steps desincronizados** — Backend envia 9 steps, frontend exibe 8 com nomes errados a partir do step 4.
2. **Modelo hardcoded errado** — Frontend (linha 933) envia `deepseek/deepseek-chat`, backend default é `deepseek/deepseek-v3.2`.
3. **Sem `ws.onclose` handler** — Se o servidor cair no meio da geração, a UI fica presa sem aviso.

### 🟡 Validações ausentes

4. Só o Step 0 valida. Steps 1 (keywords) e 2 (locais) não bloqueiam formulário vazio.
5. Domínio não é obrigatório — silenciosamente usa `'meu-site.com.br'`.
6. Sem validação de telefone WhatsApp.

### 🟡 UX / Resiliência

7. Sem botão de retry em caso de erro.
8. Campos `worker_url` e `client_token` ausentes no frontend (backend já suporta).

### 🟢 Testes

9. `test_server.py` inexistente — zero cobertura de `_build_config()` e `/api/upload-csv`.

## Fases de Execução

| Fase | O quê | Arquivo |
|---|---|---|
| 1 | Bug fixes (steps, modelo, ws.onclose) | `frontend/index.html` |
| 2 | Validações (Step 0, 1, 2) | `frontend/index.html` |
| 3 | Campos de leads (worker_url, client_token) | `frontend/index.html` |
| 4 | Testes automatizados | `tests/test_server.py` (NOVO) |
| 5 | Teste manual E2E completo | browser |

## Verification Plan

### Automated
```bash
pytest tests/test_server.py -v
pytest tests/ --cov=core --cov-fail-under=75
```

### Manual
- Teste visual completo no browser passando por cada tela
- Geração E2E de um site real e validação do ZIP descompactado

## Status

- [x] Fase 1: Bug Fixes
- [x] Fase 2: Validações
- [x] Fase 3: Campos de Leads
- [x] Fase 4: Testes Automatizados
- [ ] Fase 5: Teste E2E Manual
