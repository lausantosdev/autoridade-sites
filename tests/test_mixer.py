"""Testes para core/mixer.py"""
import pytest
from core.mixer import mix_keywords_locations, get_summary


class TestMixKeywordsLocations:
    def test_product_count(self):
        pages = mix_keywords_locations(["Piso", "Porcelanato"], ["SP", "ABC", "Guarulhos"])
        assert len(pages) == 6

    def test_page_keys(self):
        pages = mix_keywords_locations(["Piso"], ["SP"])
        assert set(pages[0].keys()) == {"title", "keyword", "location", "slug", "filename"}

    def test_filename_ends_with_html(self):
        pages = mix_keywords_locations(["Piso"], ["SP"])
        assert pages[0]["filename"].endswith(".html")

    def test_slug_is_url_safe(self):
        pages = mix_keywords_locations(["Instalação Piso"], ["São Paulo"])
        slug = pages[0]["slug"]
        assert slug == "instalacao-piso-sao-paulo"

    def test_empty_keywords(self):
        assert mix_keywords_locations([], ["SP"]) == []

    def test_empty_locations(self):
        assert mix_keywords_locations(["Piso"], []) == []


class TestGetSummary:
    def test_format(self):
        pages = mix_keywords_locations(["Piso", "Porcelanato"], ["SP", "ABC"])
        summary = get_summary(pages)
        assert "2 palavras-chave" in summary
        assert "2 locais" in summary
        assert "4 páginas" in summary

    def test_single_page(self):
        pages = mix_keywords_locations(["Piso"], ["SP"])
        summary = get_summary(pages)
        assert "1 palavras-chave" in summary
        assert "1 locais" in summary
        assert "1 páginas" in summary
