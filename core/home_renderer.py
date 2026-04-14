"""
Home Renderer — Gera o index.html da home page a partir de site_data e templates/index.html.

Substitui o inject_template() do template_injector.py (React/CSR) por geração HTML estática pura.
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from core.utils import hex_to_rgb
from core.logger import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = Path("templates")
ICON_MAP = {
    "Zap": "fas fa-bolt",
    "Shield": "fas fa-shield-halved",
    "Star": "fas fa-star",
    "Users": "fas fa-users",
    "Phone": "fas fa-phone",
    "MapPin": "fas fa-map-marker-alt",
    "Building": "fas fa-building",
    "Activity": "fas fa-chart-line",
    "CheckCircle": "fas fa-check-circle",
    "Globe": "fas fa-globe",
    "Headphones": "fas fa-headset",
    "Briefcase": "fas fa-briefcase",
    "TrendingUp": "fas fa-chart-line",
    "Settings2": "fas fa-gear",
    "Sparkles": "fas fa-wand-magic-sparkles",
    "Cpu": "fas fa-microchip",
    "Fingerprint": "fas fa-fingerprint",
    "Pencil": "fas fa-pencil",
    "Monitor": "fas fa-desktop",
    "PenTool": "fas fa-pen-ruler",
    "Layout": "fas fa-table-columns",
    "Database": "fas fa-database",
    "HeartPulse": "fas fa-heart-pulse",
}


def render_home(site_data: dict, output_dir: str, hero_image_path: str = None) -> str:
    """
    Gera o index.html da home page a partir de site_data + templates/index.html.

    Args:
        site_data: dict retornado por build_site_data()
        output_dir: diretório de saída (ex: output/dominio.com.br/)
        hero_image_path: caminho da imagem hero gerada (será copiada para output/images/hero.webp)

    Returns:
        Caminho do index.html gerado.
    """
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template não encontrado: {template_path}")

    os.makedirs(output_dir, exist_ok=True)

    html = template_path.read_text(encoding="utf-8")

    # 1. Substituir todos os placeholders simples
    html = _replace_placeholders(html, site_data)

    # 2. Injetar schema JSON-LD
    html = _inject_schema(html, site_data)

    # 3. Injetar serviços em HTML estático
    html = _inject_services(html, site_data)

    # 4. Copiar hero image
    _copy_hero(hero_image_path, output_dir)

    # 5. Salvar index.html
    output_path = Path(output_dir) / "index.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info("Home page estática gerada: %s", output_path)
    return str(output_path)


def _replace_placeholders(html: str, site_data: dict) -> str:
    """Substitui todos os {{placeholders}} simples no template."""
    empresa = site_data["empresa"]
    theme = site_data["theme"]
    seo = site_data["seo"]
    links = site_data["links"]
    leads = site_data["leads"]
    footer = site_data["footer"]

    # Calcular cor_marca_text_rgb
    from core.utils import hex_to_rgb
    rt, gt, bt = hex_to_rgb(theme["colorText"])

    # Gerar HTML do footer
    endereco = empresa.get("endereco", "").strip()
    endereco_footer = f'<p><i class="fas fa-location-dot"></i> {endereco}</p>' if endereco else ""

    slug_map = footer["slugMap"].get("servicos", {})
    cidade = seo.get("local", "")
    servicos_footer_lines = []
    for label in footer["servicos"]:
        slug = slug_map.get(label, "")
        if slug:
            servicos_footer_lines.append(f'<a href="{slug}" title="{label} em {cidade}">{label}</a>')
        else:
            servicos_footer_lines.append(f'<a href="mapa-do-site.html">{label}</a>')
    servicos_footer = "\n".join(servicos_footer_lines)

    locais_footer = "\n".join(
        f'<p><i class="fas fa-map-marker-alt"></i> {local}</p>'
        for local in footer["cidades"]
    )

    replacements = {
        "{{theme_mode}}":           theme["mode"],
        "{{empresa_nome}}":         empresa["nome"],
        "{{empresa_categoria}}":    empresa["categoria"],
        "{{cidade_principal}}":     seo.get("local", ""),
        "{{dominio}}":              empresa["dominio"],
        "{{cor_marca}}":            theme["color"],
        "{{cor_marca_rgb}}":        theme["colorRgb"],
        "{{cor_marca_text}}":       theme["colorText"],
        "{{cor_marca_text_rgb}}":   f"{rt}, {gt}, {bt}",
        "{{telefone_display}}":     empresa.get("telefoneDisplay", ""),
        "{{telefone_whatsapp}}":    empresa.get("telefoneWhatsapp", ""),
        "{{whatsapp_link}}":        links.get("whatsapp", ""),
        "{{horario}}":              empresa.get("horario", ""),
        "{{google_maps_url}}":      links.get("googleMapsEmbed", ""),
        "{{ano}}":                  empresa.get("ano", str(datetime.now().year)),
        "{{worker_url}}":           leads.get("workerUrl", ""),
        "{{client_token}}":         leads.get("clientToken", ""),
        "{{endereco_footer}}":      endereco_footer,
        "{{servicos_footer}}":      servicos_footer,
        "{{locais_footer}}":        locais_footer,
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value or "")

    return html


def _inject_schema(html: str, site_data: dict) -> str:
    """Injeta os blocos JSON-LD do Schema no <head>."""
    schema = site_data.get("schema", {})
    blocks = []

    lb = schema.get("localBusiness", "")
    if lb:
        try:
            lb_obj = json.loads(lb) if isinstance(lb, str) else lb
            lb_str = json.dumps(lb_obj, ensure_ascii=False, indent=2)
        except Exception:
            lb_str = lb
        blocks.append(f'<script type="application/ld+json">\n{lb_str}\n</script>')

    faq = schema.get("faqPage", "")
    if faq:
        try:
            faq_obj = json.loads(faq) if isinstance(faq, str) else faq
            faq_str = json.dumps(faq_obj, ensure_ascii=False, indent=2)
        except Exception:
            faq_str = faq
        blocks.append(f'<script type="application/ld+json">\n{faq_str}\n</script>')

    schema_html = "\n    ".join(blocks)

    # O template tem o bloco de Schema como texto fixo (linhas 19-36).
    # Substituir o bloco existente pelo conteúdo real.
    # Estratégia: substituir o bloco entre <!-- Schema Markup --> e o </script> final
    import re
    html = re.sub(
        r'<!-- Schema Markup -->.*?</script>',
        f'<!-- Schema Markup -->\n    {schema_html}',
        html,
        flags=re.DOTALL
    )
    return html


def _inject_services(html: str, site_data: dict) -> str:
    """Injeta os cards de serviço em HTML estático na seção #servicos."""
    items = site_data.get("featuresSection", {}).get("items", [])
    if not items:
        return html

    cards_html = ""
    for item in items:
        fa_class = ICON_MAP.get(item.get("iconName", "Zap"), "fas fa-check")
        title = item.get("title", "")
        desc = item.get("description", "")
        cards_html += (
            f'\n                <div class="service-card reveal">'
            f'\n                    <div class="service-icon"><i class="{fa_class}"></i></div>'
            f'\n                    <h3>{title}</h3>'
            f'\n                    <p>{desc}</p>'
            f'\n                </div>'
        )

    # Injetar no container de serviços
    html = html.replace(
        '<!-- Injetado via JS -->',
        cards_html
    )

    # Tornar a seção visível
    html = html.replace(
        '<section id="servicos" class="section section-alt" style="display: none;">',
        '<section id="servicos" class="section section-alt">'
    )

    return html


def _copy_hero(hero_image_path: str, output_dir: str):
    """Copia a imagem hero para output/images/hero.webp."""
    if not hero_image_path or not os.path.exists(hero_image_path):
        return
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    dest = images_dir / "hero.webp"
    if os.path.abspath(hero_image_path) != os.path.abspath(dest):
        shutil.copy2(hero_image_path, dest)
