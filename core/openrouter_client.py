"""
OpenRouter Client - Client unificado para API do OpenRouter (compatível com OpenAI SDK)
"""
import os
import json
import time
import threading
import httpx
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
from json_repair import repair_json
from core.logger import get_logger
from core.exceptions import ConfigError
logger = get_logger(__name__)

# Timeout explícito por fase:
#   connect=10s  — falha rápida se o servidor não responder à conexão
#   read=90s     — conteúdo SEO longo (900+ palavras) pode demorar; 90s evita hang silencioso
#   pool=5s      — aquisição de conexão do pool HTTP
HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=5.0)

# Cascata de modelos usada quando o modelo primário gera JSON malformado.
# Ordem: barato/rápido → mais confiável para JSON com pt-BR utf-8
_FALLBACK_MODELS = [
    "google/gemini-2.0-flash-001",   # fallback 1: excelente UTF-8, muito barato
    "openai/gpt-4o-mini",            # fallback 2: JSON extremamente consistente
]

load_dotenv()


class OpenRouterClient:
    """Client para OpenRouter API, usando SDK OpenAI (compatível)."""

    def __init__(self, model: str = "deepseek/deepseek-chat", max_retries: int = 3):
        api_key = os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            raise ConfigError(
                "OPENROUTER_API_KEY não encontrada. "
                "Crie um arquivo .env com: OPENROUTER_API_KEY=sk-or-v1-sua-chave"
            )

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=HTTP_TIMEOUT,  # httpx.Timeout com connect/read distintos
            max_retries=0,  # Desativa retry interno do SDK (usamos o nosso customizado)
            http_client=httpx.Client(timeout=HTTP_TIMEOUT),
        )
        self.model = model
        self.fallback_models = _FALLBACK_MODELS
        self.max_retries = max_retries
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._lock = threading.Lock()

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict | None:
        """
        Chama a API e retorna a resposta parseada como JSON.

        Estratégia de resiliência em duas camadas:
        - Opção A: json_repair tenta consertar JSON malformado (escapes Unicode inválidos,
          vírgulas extras, etc.) antes de escalar para um modelo diferente.
        - Opção B: Model Fallback Cascading — se o modelo primário falhar por JSON mesmo
          após reparo, tenta modelos fallback (gemini-flash -> gpt-4o-mini).

        Rate limit e erros de rede continuam com retry no modelo atual.
        """
        models_to_try = [self.model] + self.fallback_models

        for model_idx, current_model in enumerate(models_to_try):
            # Modelo primário usa max_retries; modelos fallback têm 1 tentativa cada
            max_tries = self.max_retries if model_idx == 0 else 1

            for attempt in range(max_tries):
                try:
                    response = self.client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        extra_headers={
                            "HTTP-Referer": "https://autoridade-sites.local",
                            "X-Title": "SiteGen SEO Generator"
                        }
                    )

                    with self._lock:
                        self._call_count += 1
                        if response.usage:
                            self._total_input_tokens += response.usage.prompt_tokens
                            self._total_output_tokens += response.usage.completion_tokens

                    content = response.choices[0].message.content

                    # Opção A: parse direto; se falhar, tenta json_repair
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        repaired = repair_json(content)
                        parsed = json.loads(repaired)
                        logger.warning(
                            "JSON reparado via json_repair [model: %s, attempt: %d]",
                            current_model, attempt + 1
                        )
                        return parsed

                except RateLimitError:
                    wait = 20 + (attempt * 10)
                    logger.warning(
                        "Rate limit (429) [%s] — aguardando %ds antes do retry %d/%d",
                        current_model, wait, attempt + 1, max_tries
                    )
                    if attempt < max_tries - 1:
                        time.sleep(wait)

                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout) as e:
                    # Timeout explícito: loga com contexto claro e faz retry rápido
                    logger.warning(
                        "⏱ Timeout HTTP [%s] attempt %d/%d: %s — retrying...",
                        current_model, attempt + 1, max_tries, type(e).__name__
                    )
                    if attempt < max_tries - 1:
                        time.sleep(3)  # Backoff fixo curto para timeouts

                except Exception as e:
                    logger.warning(
                        "Tentativa %d/%d [%s] falhou: %s",
                        attempt + 1, max_tries, current_model, e
                    )
                    if attempt < max_tries - 1:
                        time.sleep(2 ** attempt)

            # Opção B: modelo atual esgotou tentativas — escala para próximo
            if model_idx < len(models_to_try) - 1:
                next_model = models_to_try[model_idx + 1]
                logger.warning(
                    "Modelo '%s' falhou — escalando para fallback: %s",
                    current_model, next_model
                )

        logger.error("Todos os modelos falharam ao gerar JSON válido")
        return None

    def generate_text(self, system_prompt: str, user_prompt: str) -> str | None:
        """Chama a API e retorna texto puro (sem JSON)."""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    extra_headers={
                        "HTTP-Referer": "https://autoridade-sites.local",
                        "X-Title": "SiteGen SEO Generator"
                    }
                )

                with self._lock:
                    self._call_count += 1
                    if response.usage:
                        self._total_input_tokens += response.usage.prompt_tokens
                        self._total_output_tokens += response.usage.completion_tokens

                return response.choices[0].message.content

            except RateLimitError as e:
                wait = 20 + (attempt * 10)
                logger.warning("Rate limit (429) — aguardando %ds antes do retry %d/%d", wait, attempt + 1, self.max_retries)
                if attempt < self.max_retries - 1:
                    time.sleep(wait)
            except Exception as e:
                logger.warning("Tentativa %d/%d falhou: %s", attempt + 1, self.max_retries, e)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso da API."""
        # Preços do DeepSeek V3.2 via OpenRouter ($0.26/M input, $0.38/M output)
        input_cost = (self._total_input_tokens / 1_000_000) * 0.26
        output_cost = (self._total_output_tokens / 1_000_000) * 0.38
        return {
            'calls': self._call_count,
            'input_tokens': self._total_input_tokens,
            'output_tokens': self._total_output_tokens,
            'total_tokens': self._total_input_tokens + self._total_output_tokens,
            'cost_usd': round(input_cost + output_cost, 4),
            'cost_brl': round((input_cost + output_cost) * 5.8, 2),  # Estimativa
        }
