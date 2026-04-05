"""Testes para funções puras em core/topic_generator.py."""
import json
import os
import time
from unittest.mock import MagicMock, patch
from core.topic_generator import (
    _safe_filename, _fallback_topics, get_random_mix,
    generate_topics, CACHE_TTL_SECONDS,
)


class TestSafeFilename:
    def test_simple_ascii(self):
        assert _safe_filename("Hello World") == "hello_world"

    def test_accented_chars(self):
        result = _safe_filename("Instalação de Piso")
        assert 'instalacao' in result
        assert 'piso' in result

    def test_special_chars_removed(self):
        result = _safe_filename("limpeza & higienização!!!")
        assert '&' not in result
        assert '!' not in result

    def test_strip_underscores(self):
        result = _safe_filename("  test  ")
        assert not result.startswith('_')
        assert not result.endswith('_')


class TestFallbackTopics:
    def test_returns_required_keys(self):
        result = _fallback_topics("Limpeza")
        assert 'palavras' in result
        assert 'frases' in result

    def test_palavras_not_empty(self):
        result = _fallback_topics("Piso")
        assert len(result['palavras']) >= 10

    def test_frases_contain_categoria(self):
        result = _fallback_topics("Barbearia")
        for frase in result['frases']:
            assert 'Barbearia' in frase

    def test_different_categorias_different_frases(self):
        r1 = _fallback_topics("Piso")
        r2 = _fallback_topics("Barbearia")
        assert r1['frases'] != r2['frases']


class TestGetRandomMix:
    def test_returns_correct_count(self):
        topics = {'palavras': ['a', 'b', 'c'], 'frases': ['x', 'y', 'z']}
        result = get_random_mix(topics, count=4)
        assert len(result) == 4

    def test_default_count_is_6(self):
        topics = {'palavras': ['a'], 'frases': ['x']}
        result = get_random_mix(topics)
        assert len(result) == 6

    def test_handles_empty_palavras(self):
        topics = {'palavras': [], 'frases': ['x', 'y']}
        result = get_random_mix(topics, count=3)
        assert len(result) == 3

    def test_handles_empty_frases(self):
        topics = {'palavras': ['a', 'b'], 'frases': []}
        result = get_random_mix(topics, count=2)
        assert len(result) == 2

    def test_handles_both_empty(self):
        topics = {'palavras': [], 'frases': []}
        result = get_random_mix(topics, count=3)
        assert len(result) == 3


class TestCacheTTL:
    """Testes para expiração do cache de tópicos (TTL 7 dias)."""

    def _make_config(self, categoria="Barbearia"):
        return {"empresa": {"categoria": categoria}}

    def _write_cache(self, cache_dir, categoria, age_seconds=0):
        """Escreve um arquivo de cache com idade controlada."""
        os.makedirs(cache_dir, exist_ok=True)
        safe_name = _safe_filename(categoria)
        path = os.path.join(cache_dir, f"topicos_{safe_name}.json")
        data = {"palavras": ["cached_word"], "frases": ["cached_phrase"]}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        # Ajustar mtime para simular idade
        if age_seconds > 0:
            old_time = time.time() - age_seconds
            os.utime(path, (old_time, old_time))
        return path

    @patch("core.topic_generator.CACHE_DIR")
    def test_fresh_cache_returns_cached_data(self, mock_cache_dir, tmp_path):
        """Cache com menos de 7 dias deve retornar dados do disco sem chamar a API."""
        cache_dir = str(tmp_path / "cache")
        mock_cache_dir.__str__ = lambda s: cache_dir
        
        # Patch CACHE_DIR diretamente no módulo
        with patch("core.topic_generator.CACHE_DIR", cache_dir):
            self._write_cache(cache_dir, "Barbearia", age_seconds=3600)  # 1 hora
            mock_client = MagicMock()
            config = self._make_config("Barbearia")
            
            result = generate_topics(config, mock_client)
            
            assert result["palavras"] == ["cached_word"]
            mock_client.generate_json.assert_not_called()

    def test_expired_cache_regenerates(self, tmp_path):
        """Cache expirado (>7 dias) deve chamar a API novamente."""
        cache_dir = str(tmp_path / "cache")
        
        with patch("core.topic_generator.CACHE_DIR", cache_dir):
            self._write_cache(cache_dir, "Barbearia", age_seconds=CACHE_TTL_SECONDS + 3600)
            
            mock_client = MagicMock()
            mock_client.generate_json.return_value = {
                "palavras": ["new_word"],
                "frases": ["new_phrase"]
            }
            config = self._make_config("Barbearia")
            
            result = generate_topics(config, mock_client)
            
            assert result["palavras"] == ["new_word"]
            mock_client.generate_json.assert_called_once()

    def test_force_bypasses_fresh_cache(self, tmp_path):
        """Flag force=True deve ignorar cache mesmo se fresco."""
        cache_dir = str(tmp_path / "cache")
        
        with patch("core.topic_generator.CACHE_DIR", cache_dir):
            self._write_cache(cache_dir, "Barbearia", age_seconds=60)  # 1 minuto
            
            mock_client = MagicMock()
            mock_client.generate_json.return_value = {
                "palavras": ["forced_word"],
                "frases": ["forced_phrase"]
            }
            config = self._make_config("Barbearia")
            
            result = generate_topics(config, mock_client, force=True)
            
            assert result["palavras"] == ["forced_word"]
            mock_client.generate_json.assert_called_once()
