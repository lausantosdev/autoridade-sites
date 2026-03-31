"""
Mixer - Gera o produto cartesiano de palavras-chave × locais
"""
from core.utils import slugify


def mix_keywords_locations(keywords: list, locations: list) -> list:
    """
    Gera todas as combinações de palavras-chave × locais.

    Returns:
        Lista de dicts com 'title' e 'slug' para cada combinação.
    """

    pages = []
    for kw in keywords:
        for loc in locations:
            title = f"{kw} {loc}"
            pages.append({
                'title': title,
                'keyword': kw,
                'location': loc,
                'slug': slugify(title),
                'filename': f"{slugify(title)}.html"
            })

    return pages


def get_summary(pages: list) -> str:
    """Retorna resumo do mix gerado."""
    keywords = set(p['keyword'] for p in pages)
    locations = set(p['location'] for p in pages)
    return (
        f"{len(keywords)} palavras-chave × {len(locations)} locais = "
        f"{len(pages)} páginas"
    )
