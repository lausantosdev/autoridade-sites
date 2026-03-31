"""
Template Injector — Injeta dados do site no template SiteGen pré-buildado.

Pega o dist/index.html (build único do template) e injeta:
1. window.__SITE_DATA__ (dados do site em JSON)
2. Meta tags SEO (<title>, <meta>, og:tags)
3. Schema JSON-LD (LocalBusiness + FAQPage)
4. Copia assets (JS/CSS bundled + hero image) para o output

Output: um index.html completo com design premium SiteGen + dados do cliente.
"""
import os
import json
import shutil
from pathlib import Path


# Caminho padrão do dist/ commitado no repo
TEMPLATE_DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'template-dist')


def inject_template(
    site_data: dict,
    output_dir: str,
    dist_dir: str = None,
    hero_image_path: str = None,
) -> str:
    """
    Injeta os dados do site no template SiteGen pré-buildado.
    
    Args:
        site_data: dict compliant com SiteData (gerado por site_data_builder)
        output_dir: diretório de saída (ex: output/cleanproestofados.com.br/)
        dist_dir: caminho do dist/ SiteGen (default: template-dist/ no repo)
        hero_image_path: caminho da hero image gerada (copiada para output)
        
    Returns:
        Caminho do index.html gerado
    """
    dist_dir = dist_dir or TEMPLATE_DIST_DIR
    dist_index = os.path.join(dist_dir, 'index.html')
    
    if not os.path.exists(dist_index):
        raise FileNotFoundError(
            f"Template SiteGen não encontrado em {dist_index}. "
            f"Execute 'npm run build' na pasta do template e copie o dist/ para template-dist/."
        )
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Ler o template pré-buildado
    with open(dist_index, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 2. Injetar meta tags SEO
    html = _inject_meta_tags(html, site_data)
    
    # 3. Injetar Schema JSON-LD
    html = _inject_schema(html, site_data)
    
    # 4. Injetar window.__SITE_DATA__ (o principal)
    html = _inject_site_data(html, site_data)
    
    # 5. Copiar assets (JS/CSS bundles)
    _copy_assets(dist_dir, output_dir)
    
    # 6. Copiar hero image se fornecida (e se não for o mesmo arquivo)
    if hero_image_path and os.path.exists(hero_image_path):
        dest = os.path.join(output_dir, 'hero-image.jpg')
        if os.path.abspath(hero_image_path) != os.path.abspath(dest):
            shutil.copy2(hero_image_path, dest)
    
    # 7. Copiar favicon
    favicon_src = os.path.join(dist_dir, 'favicon.svg')
    if os.path.exists(favicon_src):
        shutil.copy2(favicon_src, os.path.join(output_dir, 'favicon.svg'))
    
    # 8. Salvar o index.html final
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  ✓ Home page SiteGen gerada: {output_path}")
    return output_path


def _inject_meta_tags(html: str, site_data: dict) -> str:
    """Substitui os marcadores de meta tags pelos valores reais."""
    seo = site_data.get('seo', {})
    theme = site_data.get('theme', {})
    
    replacements = {
        '__SITE_TITLE__': seo.get('title', ''),
        '__SITE_META_DESC__': seo.get('metaDescription', ''),
        '__SITE_META_KEYWORDS__': seo.get('metaKeywords', ''),
        '__SITE_OG_TITLE__': seo.get('ogTitle', seo.get('title', '')),
        '__SITE_OG_DESC__': seo.get('ogDescription', seo.get('metaDescription', '')),
        '__SITE_THEME_COLOR__': theme.get('color', '#000000'),
    }
    
    for marker, value in replacements.items():
        html = html.replace(marker, _escape_html_attr(str(value)))
    
    return html


def _inject_schema(html: str, site_data: dict) -> str:
    """Injeta os blocos de Schema JSON-LD no <head>."""
    schema = site_data.get('schema', {})
    blocks = []
    
    # LocalBusiness
    lb = schema.get('localBusiness', '')
    if lb:
        # Formatar para legibilidade
        try:
            lb_obj = json.loads(lb) if isinstance(lb, str) else lb
            lb_formatted = json.dumps(lb_obj, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            lb_formatted = lb
        blocks.append(f'<script type="application/ld+json">\n{lb_formatted}\n</script>')
    
    # FAQPage
    faq = schema.get('faqPage', '')
    if faq:
        try:
            faq_obj = json.loads(faq) if isinstance(faq, str) else faq
            faq_formatted = json.dumps(faq_obj, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            faq_formatted = faq
        blocks.append(f'<script type="application/ld+json">\n{faq_formatted}\n</script>')
    
    schema_html = '\n    '.join(blocks) if blocks else ''
    return html.replace('<!-- SCHEMA_INJECT -->', schema_html)


def _inject_site_data(html: str, site_data: dict) -> str:
    """Injeta o objeto SiteData como window.__SITE_DATA__ via <script>."""
    # Serializar o JSON de forma compacta (sem indentação) para produção
    json_str = json.dumps(site_data, ensure_ascii=False, separators=(',', ':'))
    
    # Escapar </script> dentro do JSON (caso algum valor contenha)
    json_str = json_str.replace('</script>', '<\\/script>')
    
    script_tag = f'<script>window.__SITE_DATA__={json_str}</script>'
    return html.replace('<!-- SITE_DATA_INJECT -->', script_tag)


def _copy_assets(dist_dir: str, output_dir: str):
    """Copia a pasta assets/ do dist para o output (JS/CSS bundled)."""
    src_assets = os.path.join(dist_dir, 'assets')
    dst_assets = os.path.join(output_dir, 'assets')
    
    if os.path.exists(src_assets):
        # Remover assets anteriores se existirem
        if os.path.exists(dst_assets):
            shutil.rmtree(dst_assets)
        shutil.copytree(src_assets, dst_assets)


def _escape_html_attr(value: str) -> str:
    """Escapa caracteres especiais para uso em atributos HTML."""
    return (
        value
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
