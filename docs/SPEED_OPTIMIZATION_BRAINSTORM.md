# Brainstorm: Otimização de Velocidade do Pipeline SiteGen

> **Data:** 05/04/2026
> **Status:** ✅ Otimizações 1 e 2 implementadas — Otimização 3 aguardando slot
> **Sessão:** Sessão 10 (brainstorm) → Sessão 15 (implementação opt. 1+2)

---

## Contexto

O pipeline atual demora ~7.5 min para gerar um site de 90 páginas (plano Profissional).
O gargalo principal está na geração de tokens pelo modelo (DeepSeek V3.2 = 11 tok/s).

### Volumes reais do produto (baseado nos planos de preço)

| Plano | Páginas | Preço |
|---|---|---|
| Profissional | 90 | R$1.449 + R$249/mês |
| Avançado | 450 | R$4.997 + R$497/mês |
| Autoridade | 1.350 | R$12.000 + R$1.000/mês |

---

## Otimizações Planejadas

### Otimização 1 — Cache de Topics (risco zero) ✅ IMPLEMENTADO
- `generate_topics()` gera vocabulário temático por nicho (~90s de IA)
- Salvar em `cache/topics_{categoria}.json` com TTL de 7 dias
- Nas próximas gerações do mesmo nicho, lê do disco (~0s)
- **Ganho: ~90s por geração**
- **Arquivo:** `core/topic_generator.py`

### Otimização 2 — Paralelizar Hero + Home Data + Topics (risco zero) ✅ IMPLEMENTADO
- Hoje: 3 chamadas à IA sequenciais antes de qualquer subpágina (~175s)
- Proposta: `asyncio.gather(hero_image(), build_site_data(), generate_topics())`
- As 3 são completamente independentes entre si
- **Ganho: ~130s por geração**
- **Arquivo:** `server.py`

### Otimização 3 — Dual Client: Split do Prompt por Página (risco médio)
Cada página hoje faz 1 call que gera ~3500 tokens. Dividir em 2 calls paralelos:

**Call A — DeepSeek V3.2 (JSON estruturado, ~700 tokens output, ~60s):**
- Meta tags, Hero, Diferenciais, Autoridade, CTA, FAQ
- Precisa de precisão de JSON → DeepSeek é o mais confiável

**Call B — Qwen 3.6 Plus Free / Gemini 2.0 Flash (texto editorial, ~2800 tokens, ~61s):**
- 6 seções SEO (seo_h2_1..6 + seo_p1..6), ~900 palavras
- Texto livre não precisa de JSON estrito → modelo mais rápido funciona
- Ambos rodam em paralelo dentro do worker da página
- **Ganho por página: ~80% (de ~320s para ~60s)**
- **Arquivo:** `core/page_generator.py`

---

## Modelo para Call B — Decisão

### Candidatos analisados

| Modelo | Throughput | Custo output | Providers | Risco |
|---|---|---|---|---|
| DeepSeek V3.2 (atual) | 11 tok/s | $0.38/M | 12 | referência |
| Gemini 2.0 Flash | ~55 tok/s | ~$0.40/M | ✅ estável | baixo |
| Qwen 2.5 72B | ~40 tok/s | ~$0.40/M | 8 | baixo |
| **Qwen 3.6 Plus Free** | **46 tok/s** | **$0** | 1 (Alibaba SG) | médio* |
| Llama 3.3 70B (Groq) | ~750 tok/s | $0.09/M | Groq only | rate limit |

> *Qwen 3.6 Plus Free: lançado em 02/04/2026 (muito recente). 1 só provider. Rate limits não documentados. Mas FREE.

### Cadeia de fallback aprovada para Call B

```
1. Qwen 3.6 Plus Free        → 46 tok/s, $0     (primary)
2. Gemini 2.0 Flash          → ~55 tok/s, ~$0.40/M (fallback pago)
3. DeepSeek V3.2             → 11 tok/s, $0.38/M  (backstop final)
```

**Ajuste necessário:** handler de 429 do Call B deve ter wait de 5-8s antes de cair no próximo modelo da cadeia (não os 20-30s do padrão atual), para não desperdiçar tempo esperando modelo free se há alternativa paga disponível.

---

## Impacto por plano (estimado)

### Tempo de geração

| Plano | Páginas | Hoje | Com otimizações | Economia |
|---|---|---|---|---|
| Profissional | 90 | ~7.5 min | **~3.75 min** | -50% |
| Avançado | 450 | ~25 min | **~16 min** | -36% |
| Autoridade | 1.350 | ~70 min | **~46 min** | -34% |

### Custo de IA

| Plano | Hoje (DeepSeek) | Qwen Free aguenta | Fallback Flash | Backstop DeepSeek |
|---|---|---|---|---|
| Profissional (90 pág) | R$0,99 | **R$0,19** | ~R$0,89 | R$0,99 |
| Avançado (450 pág) | R$4,81 | **R$0,93** | ~R$4,44 | R$4,81 |
| Autoridade (1.350 pág) | R$14,50 | **~R$3** | ~R$10 | R$14,50 |

---

## Arquivos a modificar

| Arquivo | Mudança | Dependência |
|---|---|---|
| `core/topic_generator.py` | Cache em disco TTL 7d | Nenhuma |
| `server.py` | `asyncio.gather` + dual client init | Após opt. 1 |
| `core/page_generator.py` | Split prompt + inner ThreadPoolExecutor(2) | Após opt. 2 |

---

## Notas importantes para implementação

1. **Merge dos JSONs:** `{**result_a, **result_b}` — se um é None, fallback para 1 call só com DeepSeek
2. **Inner executor:** dentro de `_generate_single_page`, um `ThreadPoolExecutor(max_workers=2)` para os dois calls paralelos
3. **flash_client** separado do `client` principal — instanciado em `server.py` e passado para `generate_all_pages()`
4. **Rate limit 429 no Call B:** não esperar 20-30s, cair direto no fallback (5-8s max)
5. **Testes:** rodar `pytest --cov=core --cov-fail-under=75` após cada otimização antes de avançar para a próxima
6. **Qwen 3.6 Free** — monitorar estabilidade; se em 30 dias tiver muitos fallbacks para Flash, revisar se vale manter como primary
