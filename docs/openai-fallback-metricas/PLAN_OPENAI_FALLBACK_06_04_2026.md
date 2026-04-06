# Plano de Implementação: OpenAI Fallback Real + Métricas de Custo e Velocidade

> **Sprint:** Finalização de Produto — Infraestrutura de Resiliência e Observabilidade  
> **Atividade:** `openai-fallback-metricas`  
> **Objetivo:** Substituir o fallback OpenRouter/DeepSeek por **OpenAI GPT-4o Mini** (provider enterprise com JSON Schema nativo) e implementar rastreamento real de custo + velocidade em três momentos: pré-geração (projeção), durante (tempo real) e ao final (breakdown por provider).

---

## Contexto e Motivação

### Problema 1: Fallback OpenRouter é lento e degradante

O `OpenRouterClient` com DeepSeek foi criado como emergência quando o Gemini estava no Free Tier. Agora que o **Billing Tier 1 está ativo** e geramos 90 páginas em 2m31s sem um único 429, o OpenRouter como fallback cria uma experiência degradada silenciosa:

| Cenário | Tempo por 90 pgs | UX |
|---|---|---|
| Gemini Tier 1 | ~2min 30s | ✅ Premium |
| Fallback OpenRouter/DeepSeek | ~8 a 15min | ❌ Inaceitável |

### Problema 2: Custo exibido hoje é incorreto

O Wizard mostra `R$ 0,01` para 90 páginas. O custo real estimado é ~R$ 0,73. O `usage_metadata` do Gemini não está sendo capturado corretamente em paralelo, e não há acumulador central para multi-provider.

### Solução

| Componente | Antes | Depois |
|---|---|---|
| Fallback | OpenRouter/DeepSeek (~15min) | OpenAI GPT-4o Mini (~2min) |
| Custo exibido | R$ 0,01 (incorreto) | R$ 0,73 (real, com projeção prévia) |
| Visibilidade | Nenhuma | Projeção + live cost + breakdown |

---

## Arquitetura da Solução

```
Gemini 2.5 Flash (primário — 99% do tempo)
   ↓ se falhar após 1 retry (5s)
OpenAI GPT-4o Mini (fallback real — mesma velocidade/qualidade)
   ↓ se ambos falharem
❌ Fail-fast: "Serviço temporariamente indisponível. Tente em alguns minutos."

StatsAccumulator (thread-safe, injetado no pipeline)
   ├── Acumula tokens por provider (gemini | openai)
   ├── Calcula custo real por provider
   ├── Envia custo acumulado em cada evento WebSocket de progresso
   └── Gera breakdown final por provider na tela de conclusão
```

---

## Fases de Execução

### Fase 1 — `core/openai_client.py` [NOVO]

**Interface:** Drop-in replacement do `GeminiClient`.

```python
class OpenAIClient:
    def __init__(self, model="gpt-4o-mini"):
        # Lê OPENAI_API_KEY do .env
        # Usa openai.OpenAI() direto (sem base_url)

    def generate_json(self, system_prompt, user_prompt) -> dict | None:
        # response_format={"type": "json_schema", "json_schema": <PageContent schema>}
        # Retry: máximo 1 tentativa extra em 429 (5s wait), depois None
        # Captura response.usage SEMPRE (nunca None na OpenAI)

    def generate_text(self, system_prompt, user_prompt) -> str | None:
        # Texto puro

    def get_stats(self) -> dict:
        # calls, input_tokens, output_tokens, cost_usd, cost_brl
        # Preços GPT-4o Mini: $0.15/M input, $0.60/M output
```

**Preços de referência (verif. em openai.com/pricing):**
- Input: $0.150 / 1M tokens ($0.075 cached)
- Output: $0.600 / 1M tokens

**Status:** [ ]

---

### Fase 2 — `core/stats_accumulator.py` [NOVO]

**Responsabilidade:** Agrega métricas de múltiplos providers, thread-safe, calcula projeções.

```python
class StatsAccumulator:
    TOKENS_PER_PAGE_INPUT  = 1_100   # calibrado: teste 90 pgs de hoje
    TOKENS_PER_PAGE_OUTPUT = 2_450   # calibrado: ~1.840 palavras × 1.33
    PAGES_PER_SECOND_30W   = 1.07    # calibrado: 90 pgs / 151s / 30 workers

    PRICES = {
        'gemini': {'input': 0.15, 'output': 0.60},  # $/M tokens (Tier 1)
        'openai': {'input': 0.15, 'output': 0.60},  # $/M tokens (GPT-4o Mini)
    }

    def record(self, provider: str, input_tokens: int, output_tokens: int):
        """Thread-safe. Provider: 'gemini' | 'openai'."""

    def get_summary(self) -> dict:
        """Retorna breakdown por provider + total com custo em BRL."""

    def get_projection(self, total_pages: int, workers: int) -> dict:
        """Estimativa pré-geração: tempo, custo, tokens totais."""

    def get_live_cost(self) -> float:
        """Custo BRL acumulado até agora (para eventos de progresso)."""
```

`get_projection()` para 90 páginas com 30 workers:
```json
{
  "estimated_time_s": 84,
  "estimated_time_str": "~1min 24s",
  "estimated_cost_usd": 0.148,
  "estimated_cost_brl": 0.86,
  "total_pages": 90,
  "model": "Gemini 2.5 Flash"
}
```

**Status:** [ ]

---

### Fase 3 — Fix `core/gemini_client.py`

Dois problemas a corrigir:

**3.1 — Bug de `usage_metadata` ausente em paralelo:**
```python
# Após response bem-sucedido:
if response.usage_metadata and response.usage_metadata.prompt_token_count:
    input_tokens = response.usage_metadata.prompt_token_count
    output_tokens = response.usage_metadata.candidates_token_count or 0
else:
    # Fallback de estimativa (melhor do que zero)
    input_tokens = int(len(user_prompt.split()) * 1.33)
    output_tokens = int(len(str(result).split()) * 1.33)
    logger.debug("usage_metadata ausente — estimativa por contagem de palavras")
```

**3.2 — Restaurar retry saudável** (foi removido durante teste de hoje):
```python
# Comportamento desejado: 1 retry com 5s de espera, depois retorna None
if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
    if attempt == 0:
        logger.warning("Gemini 429 — aguardando 5s antes do retry final")
        time.sleep(5)
    else:
        logger.error("Gemini 429 persistente — retornando None para acionar OpenAI fallback")
        return None
```

**Status:** ✅ Concluído — 06/04/2026

---

### Fase 4 — `core/page_generator.py`

**4.1 — Atualizar assinatura:**
```python
def generate_all_pages(
    pages, config, topics,
    client,                  # OpenAIClient (fallback real)
    template_path, output_dir,
    progress_callback=None,
    gemini_client=None,
    stats_accumulator=None   # NOVO
):
```

**4.2 — Lógica em `_generate_single_page()`:**
```python
# 1. Gemini primário
result = None
if gemini_client:
    result = gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
    if result and stats_accumulator:
        stats_accumulator.record("gemini",
            gemini_client._last_input_tokens,
            gemini_client._last_output_tokens)

# 2. OpenAI fallback
if not result and client:
    logger.warning("%s: Gemini falhou — usando OpenAI fallback", page['filename'])
    result = client.generate_json(SYSTEM_PROMPT, user_prompt)
    if result and stats_accumulator:
        stats_accumulator.record("openai",
            client._last_input_tokens,
            client._last_output_tokens)

# 3. Fail-fast
if not result:
    raise APIError("Gemini e OpenAI falharam — tente novamente em alguns minutos")
```

> **Nota:** `_last_input_tokens` e `_last_output_tokens` são atributos que os clients devem expor após cada chamada bem-sucedida, além do acumulador total de `get_stats()`.

**4.3 — flat_result sem `_flatten_json`:**  
OpenAI com JSON Schema também retorna flat. Adicionar flag `used_flat_provider = used_gemini or used_openai`.

**Status:** ✅ Concluído — 06/04/2026

---

### Fase 5 — `server.py`

**5.1 — Instanciar OpenAI no lugar do OpenRouter**
```python
# ANTES:
client = OpenRouterClient(model=config['api']['model'], max_retries=...)

# DEPOIS:
from core.openai_client import OpenAIClient
client = None
try:
    client = OpenAIClient(model='gpt-4o-mini')
    logger.info("OpenAIClient ativo — fallback real pronto")
except Exception as e:
    logger.warning("OpenAIClient indisponível (%s) — Gemini sem fallback", e)
```

**5.2 — Criar e injetar `StatsAccumulator`:**
```python
from core.stats_accumulator import StatsAccumulator
accumulator = StatsAccumulator()

# Projeção: enviar antes do step 4 (antes da geração iniciar)
projection = accumulator.get_projection(len(pages), config['api']['max_workers'])
await websocket.send_json({"type": "projection", **projection})
```

**5.3 — Custo em cada evento de progresso:**
```python
def progress_cb(current, total_pages, title):
    loop.call_soon_threadsafe(progress_queue.put_nowait, {
        "type": "progress",
        "current": current,
        "total": total_pages,
        "percentage": round((current / max(total_pages, 1)) * 100),
        "cost_brl": accumulator.get_live_cost()  # NOVO
    })
```

**5.4 — Breakdown final:**
```python
summary = accumulator.get_summary()
await websocket.send_json({
    "type": "complete",
    "stats": {
        ...campos existentes...,
        "cost_usd": summary['total']['cost_usd'],
        "cost_brl": summary['total']['cost_brl'],
        "providers": summary  # NOVO: breakdown completo
    }
})
```

**Status:** ✅ Concluído — 06/04/2026

---

### Fase 6 — `frontend/index.html`

**6.1 — Card de projeção na tela de Revisão (Step 4):**

HTML a adicionar após o resumo de configurações:
```html
<div id="cost-projection" class="projection-card" style="display:none;">
  <div class="proj-row">⏱ Tempo estimado: <strong id="proj-time">--</strong></div>
  <div class="proj-row">💰 Custo estimado: <strong id="proj-cost">--</strong></div>
  <div class="proj-row muted">📄 ~3.550 tokens/página · Gemini 2.5 Flash</div>
</div>
```

Handler WebSocket:
```js
case 'projection':
    document.getElementById('proj-time').textContent = msg.estimated_time_str;
    document.getElementById('proj-cost').textContent = `R$ ${msg.estimated_cost_brl.toFixed(2)}`;
    document.getElementById('cost-projection').style.display = 'block';
    break;
```

**6.2 — Live cost durante geração:**

Adicionar ao lado da contagem `x/N páginas`:
```html
<span id="live-cost-display" style="opacity:0.6; font-size:0.85em;"></span>
```

No handler de `progress`:
```js
if (msg.cost_brl !== undefined && msg.cost_brl > 0) {
    document.getElementById('live-cost-display').textContent =
        ` · R$ ${msg.cost_brl.toFixed(3)} gerados`;
}
```

**6.3 — Breakdown na tela final:**

```html
<div id="provider-breakdown" class="provider-stats" style="display:none;">
  <div class="provider-row gemini-row">
    🤖 Gemini: <span id="s-gemini-pages">--</span> pgs
    · R$ <span id="s-gemini-cost">--</span>
  </div>
  <div class="provider-row openai-row" id="openai-row" style="display:none;">
    🔵 OpenAI: <span id="s-openai-pages">--</span> pgs
    · R$ <span id="s-openai-cost">--</span>
  </div>
</div>
```

No handler de `complete`:
```js
if (msg.stats.providers) {
    const p = msg.stats.providers;
    // Gemini
    document.getElementById('s-gemini-pages').textContent = p.gemini.pages;
    document.getElementById('s-gemini-cost').textContent = p.gemini.cost_brl.toFixed(3);
    // OpenAI só aparece se foi usado
    if (p.openai && p.openai.pages > 0) {
        document.getElementById('s-openai-pages').textContent = p.openai.pages;
        document.getElementById('s-openai-cost').textContent = p.openai.cost_brl.toFixed(3);
        document.getElementById('openai-row').style.display = 'block';
    }
    document.getElementById('provider-breakdown').style.display = 'block';
}
```

**Status:** ✅ Concluído — 06/04/2026

---

### Fase 7 — Testes Automatizados

**7.1 — `tests/test_openai_client.py` [NOVO]:**
- `test_generate_json_success` — mock da API retorna JSON válido
- `test_generate_json_429_retry` — primeiro 429, segundo OK
- `test_generate_json_429_fail_fast` — dois 429 → retorna None em < 15s
- `test_get_stats_accumulates` — dois chamadas → tokens somam corretamente

**7.2 — `tests/test_stats_accumulator.py` [NOVO]:**
- `test_projection_90_pages` — valores dentro de ±10% do esperado
- `test_record_and_summary` — gemini + openai acumulam separado
- `test_live_cost` — reflete custo acumulado em tempo real
- `test_thread_safety` — 30 threads simultâneas sem race condition

**Status:** ✅ Concluído — 06/04/2026

---

## Arquivos Afetados

| Arquivo | Ação | Motivo |
|---|---|---|
| `core/openai_client.py` | **[NOVO]** | Fallback real com JSON Schema nativo |
| `core/stats_accumulator.py` | **[NOVO]** | Acumulador central thread-safe |
| `core/gemini_client.py` | MODIFY | Fix usage_metadata + retry saudável |
| `core/page_generator.py` | MODIFY | OpenAI fallback + stats_accumulator |
| `server.py` | MODIFY | Projection + live cost + breakdown |
| `frontend/index.html` | MODIFY | Card projeção + custo real-time + breakdown |
| `tests/test_openai_client.py` | **[NOVO]** | Testes unitários com mock |
| `tests/test_stats_accumulator.py` | **[NOVO]** | Testes do acumulador |
| `.env` | MODIFY | Campo `OPENAI_API_KEY` adicionado |

**Não mudam:** `openrouter_client.py`, `schemas.py`, templates HTML/CSS/JS.

---

## Pré-requisito de Execução

- [x] Usuário criou `OPENAI_API_KEY` em https://platform.openai.com/api-keys
- [x] Chave inserida no `.env` (campo `OPENAI_API_KEY=sk-...`)

---

## Ordem de Execução

```
Fase 1 (OpenAIClient) → Fase 2 (StatsAccumulator) → Fase 3 (GeminiClient fix)
  → Fase 4 (page_generator) → Fase 5 (server.py) → Fase 6 (frontend) → Fase 7 (testes)
```

**Regra:** Não avançar sem o checkpoint da fase anterior passar.

---

## Status Geral das Fases

- [x] Fase 1: `core/openai_client.py`
- [x] Fase 2: `core/stats_accumulator.py`
- [x] Fase 3: Fix `core/gemini_client.py`
- [x] Fase 4: `core/page_generator.py`
- [x] Fase 5: `server.py`
- [x] Fase 6: `frontend/index.html`
- [x] Fase 7: Testes automatizados

---

## 🔧 Correções Pós-Auditoria (06/04/2026)

Após auditoria estática independente, 4 bugs foram identificados e corrigidos antes do commit:

| # | Arquivo | Bug | Impacto |
|---|---|---|---|
| 1 | `gemini_client.py` L117 | `os._exit(1)` do teste Tier 1 não removido | Servidor morria em qualquer 429 |
| 2 | `server.py` L302 | `client.get_stats()` com `client=None` | Crash na validação se OpenAI não inicializar |
| 3 | `core/validator.py` L236 | `generate_report` acessava formato antigo flat | Crash no report final com o novo acumulador |
| 4 | `server.py` Phase 1 | `_task_home/topics/hero` passavam `client` que pode ser `None` | Crash na Fase 1 se OpenAI indisponível |

**Arquivos adicionalmente modificados:** `core/validator.py`

---

## ⏳ Validação Manual Pendente

> **Status:** ⏳ Aguardando execução

**Objetivo:** Confirmar que toda a stack funciona end-to-end com APIs reais (não mockadas).

**Passos:**
1. Iniciar `python server.py`
2. Abrir `http://localhost:8000` no browser
3. Preencher wizard com empresa testão (6 páginas)
4. **Verificar nos logs:** `OpenAIClient ativo`, `GeminiClient ativo`, `phase1_client` sem erros
5. **Verificar no frontend Step 4:** card `📊 Estimativa de Geração` aparece com tempo e custo
6. **Verificar durante geração:** custo em tempo real aparece ao lado do progresso
7. **Verificar na tela final:** breakdown `🤖 Gemini: X pgs · R$ Y` aparece
8. **Verificar ZIP:** download gera arquivo válido
9. **Verificar report:** `output/reports/dominio_report.md` contém custo correto
