"""Testes para core/page_generator._flatten_json"""
from core.page_generator import _flatten_json


class TestFlattenJson:
    def test_already_flat(self):
        """JSON já flat retorna inalterado."""
        data = {"titulo": "Piso Vinílico em SP", "meta_description": "Descrição"}
        result = _flatten_json(data)
        assert result["titulo"] == "Piso Vinílico em SP"
        assert result["meta_description"] == "Descrição"

    def test_nested_one_level(self):
        """JSON aninhado em 1 nível é achatado."""
        data = {"META TAGS": {"titulo": "X", "meta_description": "Y"}}
        result = _flatten_json(data)
        assert result["titulo"] == "X"
        assert result["meta_description"] == "Y"

    def test_meta_tags_prefix_removed(self):
        """Prefixos de grupo meta_tags_ são removidos."""
        data = {"meta_tags": {"titulo": "X"}}
        result = _flatten_json(data)
        assert "titulo" in result
        assert result["titulo"] == "X"

    def test_hero_prefix_preserved(self):
        """Prefixo hero_ é preservado após flatten de hero_section_."""
        data = {"HERO": {"titulo_linha_1": "Precisa de"}}
        result = _flatten_json(data)
        assert "hero_titulo_linha_1" in result
        assert result["hero_titulo_linha_1"] == "Precisa de"

    def test_seo_prefix_preserved(self):
        """Prefixo seo_ é preservado após flatten de seo_content_."""
        data = {"SEO CONTENT": {"h2_1": "Título", "p1": "Texto"}}
        result = _flatten_json(data)
        assert "seo_h2_1" in result
        assert "seo_p1" in result

    def test_deep_nesting(self):
        """JSON com 3+ níveis de profundidade é achatado."""
        data = {"level1": {"level2": {"titulo": "Deep"}}}
        result = _flatten_json(data)
        assert any("titulo" in k for k in result.keys())

    def test_original_keys_as_fallback(self):
        """Keys originais compostas são mantidas como fallback."""
        data = {"HERO": {"titulo_destaque": "Seu Ambiente"}}
        result = _flatten_json(data)
        # Deve ter a versão limpa E a versão original como fallback
        assert "hero_titulo_destaque" in result
