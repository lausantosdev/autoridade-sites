"""
Color Utilities — Ajuste automático de contraste WCAG AA.

Garante que a cor da marca SEMPRE seja legível como texto,
independente da cor escolhida pelo cliente.

Estratégia: preserva o tom (hue) e a saturação da cor original,
ajustando apenas o brilho (lightness) até atingir contraste 4.5:1 (WCAG AA).
"""


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converte hex (#RRGGBB) para (r, g, b)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Converte (r, g, b) 0–255 para (h, s, l) onde h 0–360, s e l 0–100."""
    r_, g_, b_ = r / 255, g / 255, b / 255
    cmax = max(r_, g_, b_)
    cmin = min(r_, g_, b_)
    delta = cmax - cmin

    # Lightness
    l = (cmax + cmin) / 2

    # Saturation
    s = 0.0 if delta == 0 else delta / (1 - abs(2 * l - 1))

    # Hue
    if delta == 0:
        h = 0.0
    elif cmax == r_:
        h = 60 * (((g_ - b_) / delta) % 6)
    elif cmax == g_:
        h = 60 * (((b_ - r_) / delta) + 2)
    else:
        h = 60 * (((r_ - g_) / delta) + 4)

    return h, s * 100, l * 100


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Converte (h 0–360, s 0–100, l 0–100) para hex #RRGGBB."""
    s_ = s / 100
    l_ = l / 100
    c = (1 - abs(2 * l_ - 1)) * s_
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l_ - c / 2

    if 0 <= h < 60:
        r_, g_, b_ = c, x, 0
    elif 60 <= h < 120:
        r_, g_, b_ = x, c, 0
    elif 120 <= h < 180:
        r_, g_, b_ = 0, c, x
    elif 180 <= h < 240:
        r_, g_, b_ = 0, x, c
    elif 240 <= h < 300:
        r_, g_, b_ = x, 0, c
    else:
        r_, g_, b_ = c, 0, x

    r = round((r_ + m) * 255)
    g = round((g_ + m) * 255)
    b = round((b_ + m) * 255)

    return f'#{r:02X}{g:02X}{b:02X}'


def relative_luminance(hex_color: str) -> float:
    """Calcula a luminância relativa (WCAG 2.1) de uma cor hex."""
    r, g, b = hex_to_rgb(hex_color)

    def linearize(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color1: str, color2: str) -> float:
    """
    Calcula a relação de contraste WCAG entre duas cores hex.
    Retorna valor entre 1.0 (sem contraste) e 21.0 (máximo).
    WCAG AA exige >= 4.5 para texto normal.
    """
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_text_contrast(hex_color: str, theme_mode: str, min_ratio: float = 4.5) -> str:
    """
    Retorna uma versão da cor ajustada para garantir contraste mínimo WCAG AA
    quando usada como TEXT sobre o background do tema.

    - theme_mode='light': background é branco (#FFFFFF), cor precisa ser escura
    - theme_mode='dark':  background é escuro (#0b0d11), cor precisa ser clara

    Preserva o hue e saturação originais — só ajusta o brilho (lightness).

    Args:
        hex_color:  Cor da marca em hex (ex: '#F97316')
        theme_mode: 'light' ou 'dark'
        min_ratio:  Contraste mínimo (padrão 4.5 = WCAG AA)

    Returns:
        Hex string da cor ajustada (ex: '#C2590A')
    """
    bg = '#FFFFFF' if theme_mode == 'light' else '#0b0d11'

    # Se já passa, não precisa alterar
    if contrast_ratio(hex_color, bg) >= min_ratio:
        return hex_color

    r, g, b = hex_to_rgb(hex_color)
    h, s, l = rgb_to_hsl(r, g, b)

    step = 2.0  # ajusta 2% de lightness por iteração

    if theme_mode == 'light':
        # Escurece até atingir contraste mínimo
        while l > 0 and contrast_ratio(hsl_to_hex(h, s, l), bg) < min_ratio:
            l = max(0, l - step)
    else:
        # Clareia até atingir contraste mínimo
        while l < 100 and contrast_ratio(hsl_to_hex(h, s, l), bg) < min_ratio:
            l = min(100, l + step)

    return hsl_to_hex(h, s, l)
