"""Testes para funções puras em core/topic_generator.py."""
from core.topic_generator import _safe_filename, _fallback_topics, get_random_mix


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
