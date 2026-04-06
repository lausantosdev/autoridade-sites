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
