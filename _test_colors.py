from core.color_utils import ensure_text_contrast, contrast_ratio

colors = {
    'Amarelo puro':   '#FFD700',
    'Amber (PetVida)':'#D97706',
    'Azul':           '#2563EB',
    'Verde':          '#22C55E',
    'Vermelho':       '#EF4444',
    'Rosa':           '#EC4899',
    'Laranja':        '#F97316',
    'Ciano':          '#06B6D4',
}

print(f"{'Cor':20} {'Bruta':8} {'Ajustada':8} {'Ratio antes':12} {'Ratio depois':12} {'Mudou?'}")
print("-" * 75)
for name, c in colors.items():
    adjusted = ensure_text_contrast(c, 'light')
    ratio_before = contrast_ratio(c, '#FFFFFF')
    ratio_after = contrast_ratio(adjusted, '#FFFFFF')
    changed = 'SIM ⚠️' if c != adjusted else 'Não ✅'
    print(f"{name:20} {c:8} {adjusted:8} {ratio_before:10.1f}:1 {ratio_after:10.1f}:1   {changed}")
