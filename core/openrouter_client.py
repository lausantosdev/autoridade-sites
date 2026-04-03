"""
OpenRouter Client - Client unificado para API do OpenRouter (compatível com OpenAI SDK)
"""
import os
import json
import time
import threading
from openai import OpenAI
from dotenv import load_dotenv
from core.logger import get_logger
from core.exceptions import ConfigError
logger = get_logger(__name__)

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
            timeout=40.0,
        )
        self.model = model
        self.max_retries = max_retries
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._lock = threading.Lock()

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict | None:
        """
        Chama a API e retorna a resposta parseada como JSON.
        Usa response_format JSON e retry automático.
        """

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    extra_headers={
                        "HTTP-Referer": "https://autoridade-sites.local",
                        "X-Title": "Autoridade Sites SEO Generator"
                    }
                )

                with self._lock:
                    self._call_count += 1
                    if response.usage:
                        self._total_input_tokens += response.usage.prompt_tokens
                        self._total_output_tokens += response.usage.completion_tokens

                return json.loads(response.choices[0].message.content)

            except Exception as e:
                logger.warning("Tentativa %d/%d falhou: %s", attempt + 1, self.max_retries, e)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

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
                        "X-Title": "Autoridade Sites SEO Generator"
                    }
                )

                with self._lock:
                    self._call_count += 1
                    if response.usage:
                        self._total_input_tokens += response.usage.prompt_tokens
                        self._total_output_tokens += response.usage.completion_tokens

                return response.choices[0].message.content

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
