"""
Utils - Funções utilitárias compartilhadas
"""
import re
import unicodedata


def slugify(text: str) -> str:
    """Converte texto em slug para URL (ASCII only, lowercase, hifens)."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def hex_to_rgb(hex_color: str) -> tuple:
    """Converte cor hex para RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def adjust_color(hex_color: str, factor: float) -> str:
    """Clareia (factor > 1) ou escurece (factor < 1) uma cor hex."""
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, max(0, int(r * factor)))
    g = min(255, max(0, int(g * factor)))
    b = min(255, max(0, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"
