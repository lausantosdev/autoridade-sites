"""
GeminiClient — Client direto para Google AI Studio (Gemini API).
Usa Structured Output (Pydantic) para garantir JSON válido por contrato.
Fallback gracioso para OpenAIClient se Google falhar.
"""
import os
import time
import threading
from google import genai
from google.genai import types
from dotenv import load_dotenv
from core.schemas import PageContent
from core.logger import get_logger
from core.exceptions import ConfigError, APIError

logger = get_logger(__name__)
load_dotenv()


class GeminiClient:
    """Client direto para Google Gemini API com Structured Output."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ConfigError(
                "GEMINI_API_KEY não encontrada. "
                "Crie um arquivo .env com: GEMINI_API_KEY=sua-chave"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._lock = threading.Lock()
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._last_input_tokens = 0
        self._last_output_tokens = 0
        logger.info("GeminiClient inicializado: model=%s", model)

    def generate_page_content(
        self, system_prompt: str, user_prompt: str
    ) -> dict | None:
        """
        Gera conteúdo de página SEO com Structured Output (Pydantic).

        O Google Gemini garante que a resposta segue o schema PageContent,
        eliminando completamente erros de JSON, campos faltantes ou tipos errados.

        Returns:
            dict com todos os campos da página, ou None se falhar.
        """
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type='application/json',
                        response_schema=PageContent,
                        temperature=0.8,
                    ),
                )

                # Atualizar contadores (thread-safe)
                with self._lock:
                    self._call_count += 1
                    
                    # Capturar tokens reais (às vezes ausentes em geração paralela pesada)
                    if response.usage_metadata and response.usage_metadata.prompt_token_count:
                        input_tok  = response.usage_metadata.prompt_token_count or 0
                        output_tok = response.usage_metadata.candidates_token_count or 0
                    else:
                        import json
                        result_text = response.text if hasattr(response, 'text') and response.text else ""
                        if response.parsed:
                            result_text = json.dumps(response.parsed.model_dump())
                            
                        # Fallback: estimar por contagem de palavras × fator 1.33
                        input_tok  = int(len(user_prompt.split()) * 1.33)
                        output_tok = int(len(result_text.split()) * 1.33) if result_text else 0
                        logger.debug("usage_metadata ausente — estimativa: in=%d out=%d", input_tok, output_tok)
                
                    self._total_input_tokens += input_tok
                    self._total_output_tokens += output_tok
                    self._last_input_tokens = input_tok
                    self._last_output_tokens = output_tok

                # Structured Output: response.parsed é um PageContent validado
                if response.parsed:
                    result = response.parsed.model_dump()
                    logger.debug(
                        "Gemini OK [%s] attempt %d: %d keys",
                        self.model, attempt + 1, len(result)
                    )
                    return result

                # Fallback: tentar text se parsed não funcionou
                if response.text:
                    import json
                    result = json.loads(response.text)
                    logger.warning(
                        "Gemini parsed=None, usando text fallback [%s]",
                        self.model
                    )
                    return result

                logger.warning(
                    "Gemini retornou resposta vazia [%s] attempt %d",
                    self.model, attempt + 1
                )

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
                            "Gemini 429 persistente [%s] — retornando None para acionar OpenAI fallback",
                            self.model
                        )
                        return None
                else:
                    logger.warning(
                        "Gemini erro [%s] attempt %d/3: %s",
                        self.model, attempt + 1, e
                    )
                    if attempt < 2:
                        time.sleep(2 ** attempt)

        logger.error("GeminiClient falhou após 3 tentativas")
        return None

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict | None:
        """
        Gera JSON livre (sem response_schema) — compatível com OpenRouterClient.generate_json().

        NÃO usa PageContent schema: esse método é chamado por _generate_home_content
        que espera campos diferentes dos das subpáginas (hero_badge_text, service_N_*, etc.).
        O response_schema=PageContent fica exclusivo de generate_page_content (subpáginas).
        """
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type='application/json',
                        temperature=0.8,
                    ),
                )

                with self._lock:
                    self._call_count += 1
                    if response.usage_metadata and response.usage_metadata.prompt_token_count:
                        self._total_input_tokens  += response.usage_metadata.prompt_token_count or 0
                        self._total_output_tokens += response.usage_metadata.candidates_token_count or 0

                if response.text:
                    import json as _json
                    try:
                        return _json.loads(response.text)
                    except _json.JSONDecodeError:
                        logger.warning("generate_json: JSON malformado attempt %d — ignorando", attempt + 1)

            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    if attempt < 2:
                        logger.warning("Gemini 429 (generate_json) — aguardando 5s")
                        import time as _time; _time.sleep(5)
                    else:
                        return None
                else:
                    logger.warning("generate_json erro attempt %d/3: %s", attempt + 1, e)
                    if attempt < 2:
                        import time as _time; _time.sleep(2 ** attempt)

        return None

    def generate_text(self, system_prompt: str, user_prompt: str) -> str | None:
        """Gera texto puro (sem JSON). Usado para cena da hero image, etc."""
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.9,
                    ),
                )

                with self._lock:
                    self._call_count += 1
                    if response.usage_metadata:
                        self._total_input_tokens += (
                            response.usage_metadata.prompt_token_count or 0
                        )
                        self._total_output_tokens += (
                            response.usage_metadata.candidates_token_count or 0
                        )

                if response.text:
                    return response.text.strip()

            except Exception as e:
                if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                    if attempt == 0:
                        logger.warning("Gemini 429 (text) — aguardando 5s antes do retry final")
                        time.sleep(5)
                    else:
                        logger.error("Gemini 429 persistente (text) — retornando None")
                        return None
                else:
                    logger.warning("Erro texto attempt %d: %s", attempt + 1, e)
                    if attempt < 2:
                        time.sleep(2 ** attempt)

        return None

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso (custo zero para free tier)."""
        # Gemini 2.5 Flash via AI Studio: $0.15/M input, $0.60/M output (paid)
        # Free tier: $0.00
        input_cost = (self._total_input_tokens / 1_000_000) * 0.15
        output_cost = (self._total_output_tokens / 1_000_000) * 0.60
        return {
            'calls': self._call_count,
            'input_tokens': self._total_input_tokens,
            'output_tokens': self._total_output_tokens,
            'total_tokens': self._total_input_tokens + self._total_output_tokens,
            'cost_usd': round(input_cost + output_cost, 4),
            'cost_brl': round((input_cost + output_cost) * 5.8, 2),
        }
