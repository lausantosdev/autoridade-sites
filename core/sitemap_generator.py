"""
Sitemap Generator - Gera sitemap.xml e mapa-do-site.html
"""
import os
from datetime import datetime


def generate_sitemap(pages: list, config: dict, output_dir: str):
    """Gera sitemap.xml e mapa-do-site.html no diretório de saída."""
    domain = f"https://{config['empresa']['dominio']}"
    os.makedirs(output_dir, exist_ok=True)

    _generate_sitemap_xml(pages, domain, output_dir)
    _generate_sitemap_html(pages, domain, config, output_dir)


def _generate_sitemap_xml(pages: list, domain: str, output_dir: str):
    """Gera o sitemap.xml para indexação do Google."""
    today = datetime.now().strftime('%Y-%m-%d')

    urls = [
        f"""    <url>
        <loc>{domain}/index.html</loc>
        <lastmod>{today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>""",
        f"""    <url>
        <loc>{domain}/mapa-do-site.html</loc>
        <lastmod>{today}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>"""
    ]

    for page in pages:
        urls.append(f"""    <url>
        <loc>{domain}/{page['filename']}</loc>
        <lastmod>{today}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    path = os.path.join(output_dir, 'sitemap.xml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml)

    print(f"  ✓ sitemap.xml gerado com {len(pages) + 2} URLs")


def _generate_sitemap_html(pages: list, domain: str, config: dict, output_dir: str):
    """Gera mapa-do-site.html com links navegáveis."""
    empresa = config['empresa']['nome']
    cor = config['empresa']['cor_marca']

    links = '\n'.join(
        f'            <a href="{p["filename"]}" class="sitemap-link">{p["title"]}</a>'
        for p in pages
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapa do Site - {empresa}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ text-align: center; font-size: 2rem; margin-bottom: 10px; }}
        h1 span {{ color: {cor}; }}
        .subtitle {{ text-align: center; color: #64748b; margin-bottom: 40px; }}
        .nav-links {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 40px; }}
        .nav-links a {{ color: {cor}; text-decoration: none; font-weight: 600; font-size: 1rem; }}
        .nav-links a:hover {{ text-decoration: underline; }}
        .sitemap-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }}
        .sitemap-link {{ display: block; background: #fff; padding: 14px 18px; border-radius: 10px;
            text-decoration: none; color: #334155; font-size: 0.9rem; font-weight: 500;
            border: 1px solid #e2e8f0; transition: all 0.2s ease; }}
        .sitemap-link:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-color: {cor}; color: {cor}; }}
        .footer {{ text-align: center; margin-top: 60px; color: #94a3b8; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Mapa do Site — <span>{empresa}</span></h1>
        <p class="subtitle">Conheça todos os nossos serviços disponíveis por região</p>
        <div class="nav-links">
            <a href="index.html">← Página Inicial</a>
            <a href="sitemap.xml">Sitemap XML</a>
        </div>
        <div class="sitemap-grid">
{links}
        </div>
        <p class="footer">© {datetime.now().year} {empresa}. Todos os direitos reservados.</p>
    </div>
</body>
</html>"""

    path = os.path.join(output_dir, 'mapa-do-site.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  ✓ mapa-do-site.html gerado com {len(pages)} links")
