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
