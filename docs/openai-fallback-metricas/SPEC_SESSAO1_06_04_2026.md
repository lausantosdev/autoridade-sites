# SPEC — Sessão 1 (06/04/2026): OpenAI Fallback Real + Métricas de Custo

> **Atividade:** `openai-fallback-metricas`  
> **Plano associado:** `PLAN_OPENAI_FALLBACK_06_04_2026.md`  
> **Pré-requisito:** `OPENAI_API_KEY` preenchida no `.env`

---

## Sumário de Fases

- [ ] Fase 1: `core/openai_client.py` [NOVO]
- [ ] Fase 2: `core/stats_accumulator.py` [NOVO]
- [ ] Fase 3: Fix `core/gemini_client.py`
- [ ] Fase 4: `core/page_generator.py`
- [ ] Fase 5: `server.py`
- [ ] Fase 6: `frontend/index.html`
- [ ] Fase 7: Testes automatizados

---

## Fase 1 — `core/openai_client.py` [NOVO]

### Contexto

O SDK `openai` já está instalado (usado pelo `OpenRouterClient` via `base_url`). Aqui usamos a API oficial sem `base_url`.

### Implementação completa

```python
"""
OpenAIClient — Client direto para OpenAI API (GPT-4o Mini).
Usado como fallback real do GeminiClient.
JSON Schema nativo — sem _flatten_json(), sem json_repair.
"""
import os
import time
import threading
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
from core.schemas import PageContent
from core.logger import get_logger
from core.exceptions import ConfigError, APIError

logger = get_logger(__name__)
load_dotenv()


class OpenAIClient:
    """Client direto para OpenAI API com JSON Schema estruturado."""

    # Preços GPT-4o Mini (verificar em openai.com/pricing)
    PRICE_INPUT_PER_M  = 0.150   # USD por 1M tokens de input
    PRICE_OUTPUT_PER_M = 0.600   # USD por 1M tokens de output

    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key or api_key == 'sua-chave-aqui':
            raise ConfigError(
                "OPENAI_API_KEY não encontrada ou inválida. "
                "Configure em .env: OPENAI_API_KEY=sk-..."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._lock = threading.Lock()
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._last_input_tokens = 0   # da última chamada (para stats_accumulator)
        self._last_output_tokens = 0  # da última chamada

        logger.info("OpenAIClient inicializado: model=%s", model)

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict | None:
        """
        Gera JSON estruturado usando JSON Schema nativo da OpenAI.
        Retorna dict flat compatível com o pipeline (sem _flatten_json necessário).
        """
        # Exportar schema Pydantic para o formato que OpenAI espera
        schema = PageContent.model_json_schema()

        for attempt in range(2):  # máximo 2 tentativas (fail-fast)
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "PageContent",
                            "schema": schema,
                            "strict": True,
                        }
                    },
                    temperature=0.8,
                )

                # OpenAI sempre preenche usage — nunca None
                input_tok  = response.usage.prompt_tokens
                output_tok = response.usage.completion_tokens

                with self._lock:
                    self._call_count += 1
                    self._total_input_tokens  += input_tok
                    self._total_output_tokens += output_tok
                    self._last_input_tokens  = input_tok
                    self._last_output_tokens = output_tok

                import json
                content = response.choices[0].message.content
                result = json.loads(content)
                logger.debug("OpenAI OK [%s] attempt %d: %d keys", self.model, attempt + 1, len(result))
                return result

            except RateLimitError:
                if attempt == 0:
                    logger.warning("OpenAI 429 — aguardando 5s (última tentativa)...")
                    time.sleep(5)
                else:
                    logger.error("OpenAI 429 persistente — retornando None (fail-fast)")
                    return None

            except Exception as e:
                logger.warning("OpenAI erro attempt %d/2: %s", attempt + 1, e)
                if attempt < 1:
                    time.sleep(2)

        logger.error("OpenAIClient falhou após 2 tentativas")
        return None

    def generate_text(self, system_prompt: str, user_prompt: str) -> str | None:
        """Gera texto puro (sem JSON). Usado para hero description, tópicos, etc."""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.9,
                )
                with self._lock:
                    self._call_count += 1
                    if response.usage:
                        self._total_input_tokens  += response.usage.prompt_tokens
                        self._total_output_tokens += response.usage.completion_tokens

                return response.choices[0].message.content.strip()

            except RateLimitError:
                if attempt == 0:
                    time.sleep(5)
                else:
                    return None
            except Exception as e:
                logger.warning("OpenAI texto erro attempt %d: %s", attempt + 1, e)
                if attempt < 1:
                    time.sleep(2)

        return None

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso com custo calculado."""
        input_cost  = (self._total_input_tokens  / 1_000_000) * self.PRICE_INPUT_PER_M
        output_cost = (self._total_output_tokens / 1_000_000) * self.PRICE_OUTPUT_PER_M
        total_usd = input_cost + output_cost
        return {
            'calls': self._call_count,
            'input_tokens': self._total_input_tokens,
            'output_tokens': self._total_output_tokens,
            'total_tokens': self._total_input_tokens + self._total_output_tokens,
            'cost_usd': round(total_usd, 4),
            'cost_brl': round(total_usd * 5.8, 2),
        }
```

### Checkpoint Fase 1

```bash
python -c "
from core.openai_client import OpenAIClient
c = OpenAIClient()
result = c.generate_json('Responda em JSON.', 'Retorne: {\"titulo\": \"teste\", \"meta_description\": \"ok\"}')
print('Retornou:', type(result), '— keys:', list(result.keys())[:5] if result else 'None')
print('Stats:', c.get_stats())
"
```
> ✅ Deve retornar um dict (sem None) e stats com tokens > 0.

**Status:** [ ]

---

## Fase 2 — `core/stats_accumulator.py` [NOVO]

### Implementação completa

```python
"""
StatsAccumulator — Agrega métricas de múltiplos providers de IA (Gemini + OpenAI).
Thread-safe. Calculado por página gerada.
"""
import threading
import time
from core.logger import get_logger

logger = get_logger(__name__)

# ── Médias calibradas no teste de 90 páginas (06/04/2026) ─────────────────────
_AVG_INPUT_TOKENS_PER_PAGE  = 1_100
_AVG_OUTPUT_TOKENS_PER_PAGE = 2_450
_PAGES_PER_SECOND_30W       = 1.07   # páginas/segundo com 30 workers

# ── Preços por 1M tokens (USD) ─────────────────────────────────────────────────
_PRICES = {
    'gemini': {'input': 0.150, 'output': 0.600},  # Gemini 2.5 Flash (Tier 1)
    'openai': {'input': 0.150, 'output': 0.600},  # GPT-4o Mini
}

_BRL_RATE = 5.8  # Taxa de conversão USD → BRL (aproximada)


class StatsAccumulator:
    """Acumula tokens e custo por provider, thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._data = {
            'gemini': {'pages': 0, 'input_tokens': 0, 'output_tokens': 0},
            'openai': {'pages': 0, 'input_tokens': 0, 'output_tokens': 0},
        }

    def record(self, provider: str, input_tokens: int, output_tokens: int):
        """Registra tokens de uma página gerada. Thread-safe."""
        if provider not in self._data:
            logger.warning("Provider desconhecido: %s", provider)
            return
        with self._lock:
            self._data[provider]['pages'] += 1
            self._data[provider]['input_tokens']  += input_tokens
            self._data[provider]['output_tokens'] += output_tokens

    def _calc_cost(self, provider: str, data: dict) -> float:
        """Calcula custo em USD para um provider."""
        prices = _PRICES.get(provider, {'input': 0.15, 'output': 0.60})
        return (
            (data['input_tokens']  / 1_000_000) * prices['input'] +
            (data['output_tokens'] / 1_000_000) * prices['output']
        )

    def get_summary(self) -> dict:
        """Retorna breakdown completo por provider + total."""
        with self._lock:
            data = {k: dict(v) for k, v in self._data.items()}

        elapsed = time.time() - self._start_time
        total_pages = sum(d['pages'] for d in data.values())
        total_cost_usd = sum(self._calc_cost(p, d) for p, d in data.items())

        result = {}
        for provider, d in data.items():
            cost_usd = self._calc_cost(provider, d)
            result[provider] = {
                'pages': d['pages'],
                'input_tokens': d['input_tokens'],
                'output_tokens': d['output_tokens'],
                'cost_usd': round(cost_usd, 4),
                'cost_brl': round(cost_usd * _BRL_RATE, 3),
            }

        result['total'] = {
            'pages': total_pages,
            'cost_usd': round(total_cost_usd, 4),
            'cost_brl': round(total_cost_usd * _BRL_RATE, 3),
            'elapsed_s': round(elapsed, 1),
        }
        return result

    def get_live_cost(self) -> float:
        """Retorna custo BRL acumulado até agora (para eventos de progresso)."""
        with self._lock:
            data = {k: dict(v) for k, v in self._data.items()}
        total_usd = sum(self._calc_cost(p, d) for p, d in data.items())
        return round(total_usd * _BRL_RATE, 3)

    def get_projection(self, total_pages: int, workers: int = 30) -> dict:
        """Estimativa pré-geração: tempo, custo, tokens."""
        # Ajusta velocidade proporcionalmente aos workers
        speed = _PAGES_PER_SECOND_30W * min(workers, 30) / 30
        estimated_s = total_pages / speed if speed > 0 else 0
        mins, secs = divmod(int(estimated_s), 60)
        time_str = f"~{mins}min {secs}s" if mins > 0 else f"~{secs}s"

        total_input  = total_pages * _AVG_INPUT_TOKENS_PER_PAGE
        total_output = total_pages * _AVG_OUTPUT_TOKENS_PER_PAGE

        # Projeção assume Gemini como provider primário
        cost_usd = (
            (total_input  / 1_000_000) * _PRICES['gemini']['input'] +
            (total_output / 1_000_000) * _PRICES['gemini']['output']
        )

        return {
            'estimated_time_s':   round(estimated_s),
            'estimated_time_str': time_str,
            'estimated_cost_usd': round(cost_usd, 4),
            'estimated_cost_brl': round(cost_usd * _BRL_RATE, 3),
            'total_pages': total_pages,
            'avg_tokens_per_page': _AVG_INPUT_TOKENS_PER_PAGE + _AVG_OUTPUT_TOKENS_PER_PAGE,
            'model': 'Gemini 2.5 Flash',
        }
```

### Checkpoint Fase 2

```bash
python -c "
from core.stats_accumulator import StatsAccumulator
acc = StatsAccumulator()
# Simulando 90 páginas pelo Gemini
for _ in range(90):
    acc.record('gemini', 1100, 2450)
summary = acc.get_summary()
print('Total pages:', summary['total']['pages'])
print('Total BRL:', summary['total']['cost_brl'])
print('Gemini pages:', summary['gemini']['pages'])

# Testando projeção
proj = acc.get_projection(90, 30)
print('Proj time:', proj['estimated_time_str'])
print('Proj cost BRL:', proj['estimated_cost_brl'])
"
```
> ✅ Total pages = 90, custo total BRL próximo de R$ 0,85, projeção em torno de 1min 30s.

**Status:** [ ]

---

## Fase 3 — Fix `core/gemini_client.py`

### 3.1 — Corrigir captura de `usage_metadata`

**Localizar** o bloco (método `generate_page_content`, após `response.parsed`):
```python
# ANTES (linhas ~65-73):
with self._lock:
    self._call_count += 1
    if response.usage_metadata:
        self._total_input_tokens += (
            response.usage_metadata.prompt_token_count or 0
        )
        self._total_output_tokens += (
            response.usage_metadata.candidates_token_count or 0
        )
```

**Substituir por:**
```python
# DEPOIS:
with self._lock:
    self._call_count += 1

    # Capturar tokens reais (às vezes ausentes em geração paralela pesada)
    if response.usage_metadata and response.usage_metadata.prompt_token_count:
        input_tok  = response.usage_metadata.prompt_token_count or 0
        output_tok = response.usage_metadata.candidates_token_count or 0
    else:
        # Fallback: estimar por contagem de palavras × fator 1.33
        input_tok  = int(len(user_prompt.split()) * 1.33)
        output_tok = int(len(str(result).split()) * 1.33) if result else 0
        logger.debug("usage_metadata ausente — estimativa: in=%d out=%d", input_tok, output_tok)

    self._total_input_tokens  += input_tok
    self._total_output_tokens += output_tok
    self._last_input_tokens  = input_tok    # para stats_accumulator
    self._last_output_tokens = output_tok   # para stats_accumulator
```

> **Também adicionar** `self._last_input_tokens = 0` e `self._last_output_tokens = 0` no `__init__`.

### 3.2 — Restaurar retry saudável (1 retry com 5s)

**Localizar** o bloco de tratamento de 429 (que foi substituído na sessão de hoje pelo `os._exit(1)`) e **restaurar com a nova lógica:**

```python
# DEPOIS (comportamento correto):
except Exception as e:
    error_str = str(e)
    if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
        if attempt == 0:
            logger.warning(
                "Gemini 429 [%s] — aguardando 5s antes do retry final",
                self.model
            )
            time.sleep(5)
        else:
            logger.error(
                "Gemini 429 persistente [%s] — retornando None para acionar fallback",
                self.model
            )
            return None
    else:
        logger.warning("Gemini erro [%s] attempt %d/3: %s", self.model, attempt + 1, e)
        if attempt < 2:
            time.sleep(2 ** attempt)
```

> Fazer o mesmo ajuste no método `generate_text()`.

### Checkpoint Fase 3

```bash
pytest tests/ --cov=core --cov-fail-under=75
```
> ✅ Todos os testes existentes passam. Nenhuma regressão.

**Status:** [ ]

---

## Fase 4 — `core/page_generator.py`

### 4.1 — Atualizar assinatura de `generate_all_pages()`

```python
def generate_all_pages(
    pages: list,
    config: dict,
    topics: dict,
    client,                       # OpenAIClient (fallback real) — pode ser None
    template_path: str,
    output_dir: str,
    progress_callback=None,
    gemini_client=None,
    stats_accumulator=None        # NOVO: StatsAccumulator injetado pelo server.py
):
```

### 4.2 — Atualizar `_generate_single_page()`

**Localizar** o bloco que tenta Gemini e faz fallback (linhas ~263-276) e **substituir por:**

```python
# Tentar Gemini primeiro (structured output = JSON garantido)
result = None
used_flat = False

if gemini_client:
    result = gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
    if result:
        used_flat = True
        logger.debug("%s: Gemini OK", page['filename'])
        # Registrar no acumulador
        if stats_accumulator:
            stats_accumulator.record(
                "gemini",
                gemini_client._last_input_tokens,
                gemini_client._last_output_tokens
            )
    else:
        logger.warning("%s: Gemini falhou — acionando OpenAI fallback", page['filename'])

# Fallback: OpenAI GPT-4o Mini
if not result and client:
    result = client.generate_json(SYSTEM_PROMPT, user_prompt)
    if result:
        used_flat = True
        logger.info("%s: OpenAI fallback OK", page['filename'])
        if stats_accumulator:
            stats_accumulator.record(
                "openai",
                client._last_input_tokens,
                client._last_output_tokens
            )

# Falha total: fail-fast sem mais providers
if not result:
    raise APIError(
        "Gemini e OpenAI falharam — serviço temporariamente indisponível. "
        "Tente novamente em alguns minutos."
    )

# flat_result: ambos os providers retornam JSON flat
flat_result = result if used_flat else _flatten_json(result)
```

### Checkpoint Fase 4

```bash
pytest tests/ --cov=core --cov-fail-under=75
```
> ✅ Sem regressões.

**Status:** [ ]

---

## Fase 5 — `server.py`

### 5.1 — Imports

Adicionar no topo:
```python
from core.openai_client import OpenAIClient
from core.stats_accumulator import StatsAccumulator
```

### 5.2 — Instanciar OpenAI (substitui OpenRouter como fallback)

**Localizar** a criação do `client` (linhas ~137-140) e **substituir:**

```python
# ANTES:
client = OpenRouterClient(
    model=config['api']['model'],
    max_retries=config['api']['max_retries']
)

# DEPOIS:
client = None  # fallback opcional (OpenAI)
try:
    client = OpenAIClient(model='gpt-4o-mini')
    logger.info("OpenAIClient ativo — fallback real pronto")
except Exception as e:
    logger.warning("OpenAIClient indisponível (%s) — Gemini sem fallback", e)
```

### 5.3 — Criar acumulador e enviar projeção

**Após** a criação dos clients e **antes** do `asyncio.gather`, adicionar:

```python
# Acumulador de stats por sessão
accumulator = StatsAccumulator()

# Projeção pré-geração (enviada para o frontend antes de começar)
projection = accumulator.get_projection(
    total_pages=len(pages),
    workers=config['api']['max_workers']
)
await websocket.send_json({"type": "projection", **projection})
```

### 5.4 — Custo no progress_cb

**Localizar** a função `progress_cb` (linhas ~224-234) e **adicionar** `cost_brl`:

```python
def progress_cb(current, total_pages, title):
    completed[0] = current
    loop.call_soon_threadsafe(
        progress_queue.put_nowait,
        {
            "type": "progress",
            "current": current,
            "total": total_pages,
            "percentage": round((current / max(total_pages, 1)) * 100),
            "cost_brl": accumulator.get_live_cost(),   # NOVO
        }
    )
```

### 5.5 — Passar acumulador para `run_generation`

```python
def run_generation():
    generate_all_pages(
        pages=pages,
        config=config,
        topics=topics,
        client=client,
        template_path="templates/page.html",
        output_dir=output_dir,
        progress_callback=progress_cb,
        gemini_client=gemini,
        stats_accumulator=accumulator   # NOVO
    )
```

### 5.6 — Summary final com breakdown

**Localizar** o `await websocket.send_json({"type": "complete", ...})` e **atualizar:**

```python
summary = accumulator.get_summary()

await websocket.send_json({
    "type": "complete",
    "message": "Site gerado com sucesso!",
    "stats": {
        "pages": results['total_pages'],
        "valid": results['valid_pages'],
        "errors": len(results['errors']),
        "warnings": len(results['warnings']),
        "words": results['stats'].get('total_words', 0),
        "cost_usd": summary['total']['cost_usd'],       # ATUALIZADO (era api_stats)
        "cost_brl": summary['total']['cost_brl'],       # ATUALIZADO
        "tokens": sum(                                  # ATUALIZADO
            summary[p].get('input_tokens', 0) + summary[p].get('output_tokens', 0)
            for p in ('gemini', 'openai')
        ),
        "duration": duration_str,
        "providers": summary,                           # NOVO
    },
    "download": f"/api/download/{dominio}"
})
```

### Checkpoint Fase 5

```bash
python server.py
# Abrir localhost:8000 e gerar 6 páginas
# Confirmar no terminal: "OpenAIClient ativo" e "GeminiClient ativo"
# Confirmar evento "projection" chegando no DevTools do browser (Network → WS)
```
> ✅ Server sobe sem erros, projeção chega no frontend.

**Status:** [ ]

---

## Fase 6 — `frontend/index.html`

### 6.1 — Card de projeção na tela de Revisão (Step 4)

**Localizar** o div de review (Step 4, que mostra os dados do site) e adicionar o card **após** o resumo de custo estimado existente:

```html
<!-- Card de projeção de geração (preenchido via WebSocket 'projection') -->
<div id="gen-projection" style="
    display: none;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 16px;
    font-size: 0.88rem;
">
    <div style="font-weight:600; margin-bottom:8px; color:#a5b4fc;">📊 Estimativa de Geração</div>
    <div style="display:flex; gap:24px; flex-wrap:wrap;">
        <span>⏱ <strong id="proj-time">--</strong></span>
        <span>💰 <strong id="proj-cost">--</strong></span>
        <span style="opacity:0.6;">~3.550 tokens/pág · Gemini 2.5 Flash</span>
    </div>
</div>
```

Handler no switch do WebSocket:
```js
case 'projection':
    document.getElementById('proj-time').textContent  = msg.estimated_time_str;
    document.getElementById('proj-cost').textContent  = `R$ ${msg.estimated_cost_brl.toFixed(2)}`;
    document.getElementById('gen-projection').style.display = 'block';
    break;
```

### 6.2 — Live cost durante geração

**Localizar** o elemento que exibe `x/N páginas` durante a geração e adicionar span ao lado:

```html
<span id="live-cost-display" style="
    font-size: 0.8em;
    opacity: 0.55;
    margin-left: 8px;
"></span>
```

No handler de `progress`:
```js
case 'progress':
    // código existente...
    if (msg.cost_brl !== undefined && msg.cost_brl > 0) {
        document.getElementById('live-cost-display').textContent =
            `· R$ ${msg.cost_brl.toFixed(3)}`;
    }
    break;
```

### 6.3 — Breakdown por provider na tela final

**Localizar** onde os stats finais são exibidos e adicionar **após** o custo existente:

```html
<!-- Breakdown por provider (só aparece se providers estiver no payload) -->
<div id="provider-breakdown" style="display:none; margin-top:12px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.1);">
    <div style="font-size:0.8rem; opacity:0.6; margin-bottom:6px;">Distribuição por modelo</div>
    <div id="pb-gemini" style="font-size:0.85rem;">
        🤖 Gemini: <span id="pb-g-pages">--</span> pgs · R$ <span id="pb-g-cost">--</span>
    </div>
    <div id="pb-openai" style="display:none; font-size:0.85rem; margin-top:4px;">
        🔵 OpenAI: <span id="pb-o-pages">--</span> pgs · R$ <span id="pb-o-cost">--</span>
    </div>
</div>
```

No handler de `complete`:
```js
case 'complete':
    // código existente para mostrar stats...
    if (msg.stats && msg.stats.providers) {
        const p = msg.stats.providers;
        document.getElementById('pb-g-pages').textContent = p.gemini.pages;
        document.getElementById('pb-g-cost').textContent  = p.gemini.cost_brl.toFixed(3);
        if (p.openai && p.openai.pages > 0) {
            document.getElementById('pb-o-pages').textContent = p.openai.pages;
            document.getElementById('pb-o-cost').textContent  = p.openai.cost_brl.toFixed(3);
            document.getElementById('pb-openai').style.display = 'block';
        }
        document.getElementById('provider-breakdown').style.display = 'block';
    }
    break;
```

### Checkpoint Fase 6

- Gerar 6 páginas pelo Wizard e confirmar visualmente:
  - [ ] Card de projeção aparece na tela de Revisão com tempo e custo
  - [ ] Custo acumulado aparece ao lado de `x/6 páginas` durante geração
  - [ ] Breakdown por provider aparece na tela final
  - [ ] Custo final vs estimativa: erro ≤ 20%

**Status:** [ ]

---

## Fase 7 — Testes Automatizados

### 7.1 — `tests/test_openai_client.py` [NOVO]

```python
"""Testes do OpenAIClient com mock da API."""
import pytest
from unittest.mock import MagicMock, patch
from core.openai_client import OpenAIClient
from core.exceptions import ConfigError


class TestOpenAIClientInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        with pytest.raises(ConfigError):
            OpenAIClient()

    def test_raises_with_placeholder_key(self, monkeypatch):
        monkeypatch.setenv('OPENAI_API_KEY', 'sua-chave-aqui')
        with pytest.raises(ConfigError):
            OpenAIClient()


class TestOpenAIClientGenerateJson:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-fake-key')
        with patch('core.openai_client.OpenAI'):
            return OpenAIClient()

    def test_returns_dict_on_success(self, client):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"titulo": "Teste", "meta_description": "ok"}'
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 1200
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        result = client.generate_json("system", "user")
        assert isinstance(result, dict)
        assert result['titulo'] == 'Teste'

    def test_accumulates_tokens(self, client):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"titulo": "X", "meta_description": "y"}'
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 2000
        client.client.chat.completions.create = MagicMock(return_value=mock_response)

        client.generate_json("s", "u")
        client.generate_json("s", "u")
        stats = client.get_stats()
        assert stats['input_tokens']  == 2000
        assert stats['output_tokens'] == 4000
        assert stats['calls'] == 2

    def test_429_fail_fast_after_one_retry(self, client):
        from openai import RateLimitError
        client.client.chat.completions.create = MagicMock(
            side_effect=RateLimitError("rate limit", response=MagicMock(), body={})
        )
        import time
        start = time.time()
        result = client.generate_json("s", "u")
        elapsed = time.time() - start
        assert result is None
        assert elapsed < 15  # fail-fast: máximo ~7s (5s sleep + overhead)
```

### 7.2 — `tests/test_stats_accumulator.py` [NOVO]

```python
"""Testes do StatsAccumulator."""
import pytest
import threading
from core.stats_accumulator import StatsAccumulator


class TestStatsAccumulator:
    def test_projection_90_pages(self):
        acc = StatsAccumulator()
        proj = acc.get_projection(90, 30)
        assert proj['total_pages'] == 90
        # Tempo: entre 1 e 3 minutos (tolerância ampla)
        assert 60 <= proj['estimated_time_s'] <= 180
        # Custo: entre R$ 0,50 e R$ 1,50
        assert 0.50 <= proj['estimated_cost_brl'] <= 1.50

    def test_record_accumulates_by_provider(self):
        acc = StatsAccumulator()
        acc.record('gemini', 1000, 2000)
        acc.record('gemini', 1100, 2500)
        acc.record('openai', 900, 1800)

        summary = acc.get_summary()
        assert summary['gemini']['pages'] == 2
        assert summary['gemini']['input_tokens'] == 2100
        assert summary['openai']['pages'] == 1
        assert summary['total']['pages'] == 3

    def test_live_cost_increases(self):
        acc = StatsAccumulator()
        cost_0 = acc.get_live_cost()
        acc.record('gemini', 1100, 2450)
        cost_1 = acc.get_live_cost()
        assert cost_1 > cost_0

    def test_thread_safety(self):
        acc = StatsAccumulator()
        def record_many():
            for _ in range(100):
                acc.record('gemini', 1100, 2450)

        threads = [threading.Thread(target=record_many) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        summary = acc.get_summary()
        assert summary['gemini']['pages'] == 1000  # 10 threads × 100 registros

    def test_unknown_provider_ignored(self):
        acc = StatsAccumulator()
        acc.record('provider_invalido', 1000, 2000)  # não deve lançar, apenas logar warning
        summary = acc.get_summary()
        assert summary['total']['pages'] == 0
```

### Checkpoint Fase 7

```bash
pytest tests/test_openai_client.py -v
pytest tests/test_stats_accumulator.py -v
pytest tests/ --cov=core --cov-fail-under=75
```
> ✅ Todos os novos testes passam. Coverage ≥ 75%.

**Status:** [ ]

---

## Ordem de Execução

```
Fase 1 → Check1 → Fase 2 → Check2 → Fase 3 → Check3 →
Fase 4 → Check4 → Fase 5 → Check5 → Fase 6 → Check6 →
Fase 7 → Check Final
```

**Regra:** Não avançar para a próxima fase sem o checkpoint anterior passar.
