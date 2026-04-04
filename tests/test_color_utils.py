import pytest
from core.color_utils import (
    hex_to_rgb,
    rgb_to_hsl,
    hsl_to_hex,
    contrast_ratio,
    ensure_text_contrast,
    relative_luminance
)

class TestHexToRgb:
    def test_hex6(self):
        assert hex_to_rgb("#FF8800") == (255, 136, 0)
        
    def test_hex3(self):
        assert hex_to_rgb("#F80") == (255, 136, 0)
        
    def test_lowercase(self):
        assert hex_to_rgb("#ff8800") == (255, 136, 0)
        
    def test_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)
        
    def test_white(self):
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


class TestRgbToHsl:
    def test_black(self):
        h, s, l = rgb_to_hsl(0, 0, 0)
        assert h == 0.0
        assert s == 0.0
        assert l == 0.0
        
    def test_white(self):
        h, s, l = rgb_to_hsl(255, 255, 255)
        assert h == 0.0
        assert s == 0.0
        assert l == 100.0
        
    def test_red(self):
        h, s, l = rgb_to_hsl(255, 0, 0)
        assert h == 0.0
        assert s == 100.0
        assert l == 50.0
        
    def test_green(self):
        h, s, l = rgb_to_hsl(0, 255, 0)
        assert h == 120.0
        assert s == 100.0
        assert l == 50.0
        
    def test_blue(self):
        h, s, l = rgb_to_hsl(0, 0, 255)
        assert h == 240.0
        assert s == 100.0
        assert l == 50.0


class TestHslToHex:
    def test_roundtrip_red(self):
        r, g, b = hex_to_rgb("#FF0000")
        h, s, l = rgb_to_hsl(r, g, b)
        hex_val = hsl_to_hex(h, s, l)
        assert hex_val == "#FF0000"
        
    def test_roundtrip_blue(self):
        r, g, b = hex_to_rgb("#0000FF")
        h, s, l = rgb_to_hsl(r, g, b)
        hex_val = hsl_to_hex(h, s, l)
        assert hex_val == "#0000FF"


class TestContrastRatio:
    def test_identical_colors(self):
        assert contrast_ratio("#123456", "#123456") == 1.0
        
    def test_black_white(self):
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert ratio == pytest.approx(21.0, 0.1)
        
    def test_wcag_aa_threshold(self):
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert ratio > 4.5


class TestEnsureTextContrast:
    def test_light_mode_yellow_fails(self):
        # Amarelo puro
        yellow = "#FFFF00"
        bg_white = "#FFFFFF"
        # Sem ajuste, o contraste falha
        assert contrast_ratio(yellow, bg_white) < 4.5
        
        # Com ajuste, deve escurecer e passar
        adjusted = ensure_text_contrast(yellow, theme_mode="light")
        assert adjusted != yellow
        assert contrast_ratio(adjusted, bg_white) >= 4.5
        
    def test_dark_mode_dark_color_fails(self):
        dark_blue = "#000033"
        bg_dark = "#0b0d11"
        assert contrast_ratio(dark_blue, bg_dark) < 4.5
        
        # Com ajuste, deve clarear e passar
        adjusted = ensure_text_contrast(dark_blue, theme_mode="dark")
        assert adjusted != dark_blue
        assert contrast_ratio(adjusted, bg_dark) >= 4.5
        
    def test_already_compliant_dark(self):
        # Preto no light mode ja passa
        black = "#000000"
        bg_white = "#FFFFFF"
        assert contrast_ratio(black, bg_white) >= 4.5
        
        adjusted = ensure_text_contrast(black, theme_mode="light")
        assert adjusted == black

    def test_already_compliant_white(self):
        # Branco no dark mode ja passa
        white = "#FFFFFF"
        bg_dark = "#0b0d11"
        assert contrast_ratio(white, bg_dark) >= 4.5
        
        adjusted = ensure_text_contrast(white, theme_mode="dark")
        assert adjusted == white
        
    def test_output_is_hex_string(self):
        color = "#FACC15"
        adjusted = ensure_text_contrast(color, theme_mode="light")
        assert isinstance(adjusted, str)
        assert adjusted.startswith("#")
        assert len(adjusted) == 7
