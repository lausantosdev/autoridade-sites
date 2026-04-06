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
