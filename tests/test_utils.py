"""Testes para core/utils.py"""
import pytest
from core.utils import slugify, hex_to_rgb, adjust_color


class TestSlugify:
    def test_basic(self):
        assert slugify("Piso Vinílico São Paulo") == "piso-vinilico-sao-paulo"

    def test_removes_special_chars(self):
        assert slugify("Instalação & Reforma") == "instalacao-reforma"

    def test_collapses_multiple_spaces(self):
        assert slugify("foo   bar") == "foo-bar"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_already_slug(self):
        assert slugify("piso-vinilico") == "piso-vinilico"


class TestHexToRgb:
    def test_white(self):
        assert hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_brand_blue(self):
        assert hex_to_rgb("#2563EB") == (37, 99, 235)

    def test_no_hash(self):
        assert hex_to_rgb("2563EB") == (37, 99, 235)


class TestAdjustColor:
    def test_lighten(self):
        result = adjust_color("#808080", 1.5)
        r, g, b = hex_to_rgb(result)
        assert r > 128 and g > 128 and b > 128

    def test_darken(self):
        result = adjust_color("#808080", 0.5)
        r, g, b = hex_to_rgb(result)
        assert r < 128 and g < 128 and b < 128

    def test_caps_at_255(self):
        result = adjust_color("#ffffff", 2.0)
        assert result == "#ffffff"

    def test_floors_at_0(self):
        result = adjust_color("#000000", 0.5)
        assert result == "#000000"
