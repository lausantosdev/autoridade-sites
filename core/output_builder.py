"""
Output Builder — Setup do diretório de saída (compartilhado entre CLI e Wizard).
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

from core.config_loader import get_whatsapp_link, get_phone_display
from core.template_renderer import replace_config_vars
from core.logger import get_logger
logger = get_logger(__name__)


TEMPLATES_DIR = Path("templates")


def setup_output_dir(output_dir: str, config: dict):
    """Copia assets do template para o output e cria o JS de dados."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copiar CSS, JS, images
    for subdir in ['css', 'js', 'images']:
        src = TEMPLATES_DIR / subdir
        dst = output_path / subdir
        if src.exists():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)

    # Processar variáveis no CSS copiado
    css_path = output_path / "css" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding='utf-8')
        css_content = replace_config_vars(css_content, config)
        css_path.write_text(css_content, encoding='utf-8')

    # Criar js/dados.js
    dados_js = {
        "empresa_nome": config['empresa']['nome'],
        "empresa_categoria": config['empresa']['categoria'],
        "telefone_whatsapp": config['empresa']['telefone_whatsapp'],
        "telefone_link": f"tel:{config['empresa']['telefone_whatsapp']}",
        "telefone_display": get_phone_display(config),
        "whatsapp_link": get_whatsapp_link(config),
        "horario": config['empresa'].get('horario', ''),
        "google_maps_url": config['empresa'].get('google_maps_embed', ''),
        "dominio": config['empresa']['dominio'],
        "ano": str(datetime.now().year)
    }

    js_dst = output_path / "js"
    js_dst.mkdir(parents=True, exist_ok=True)
    dados_path = js_dst / "dados.js"

    script_content = f"// Criado automaticamente - Autoridade Sites\n"
    script_content += f"const DadosSite = {json.dumps(dados_js, indent=4, ensure_ascii=False)};\n"

    with open(dados_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    # Gerar robots.txt (essencial para SEO)
    domain = config['empresa']['dominio']
    robots_content = (
        "User-agent: *\n"
        "Disallow:\n"
        "\n"
        f"Sitemap: https://{domain}/sitemap.xml\n"
    )
    robots_path = output_path / "robots.txt"
    if not robots_path.exists():
        robots_path.write_text(robots_content, encoding='utf-8')


def generate_fallback_index(config: dict, output_dir: str):
    """Fallback: gera index.html do template HTML puro (caso SiteGen falhe)."""
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        content = index_template.read_text(encoding='utf-8')
        content = replace_config_vars(content, config)
        output_path = Path(output_dir) / "index.html"
        output_path.write_text(content, encoding='utf-8')
        logger.info("Home page fallback gerada (template HTML puro)")


def build_static_home_page(config: dict, site_data: dict, output_dir: str) -> str:
    """
    Gera index.html a partir do template estático avançado (index_static.html).

    DIFERENTE de generate_fallback_index():
        - Usa templates/index_static.html (NÃO toca templates/index.html)
        - Injeta AI data (site_data) para SEO, Hero, Serviços e FAQ nativo.
        - Retorna o caminho do index.html gerado

    Args:
        config: dict carregado via load_config().
        site_data: dict retornado por build_site_data() (contém dados gerados pela IA).
        output_dir: diretório de saída.

    Returns:
        Caminho absoluto do index.html gerado.
    """
    import re
    import json
    from pathlib import Path
    import logging
    from core.template_renderer import (
        replace_config_vars, 
        render_premium_services_html,
        render_faq_html,
        render_authority_html,
        render_bottom_cta_html
    )

    logger = logging.getLogger(__name__)
    TEMPLATES_DIR = Path("templates")

    static_template = TEMPLATES_DIR / "index_static.html"

    if not static_template.exists():
        logger.warning("index_static.html não encontrado. Usando fallback.")
        generate_fallback_index(config, output_dir)
        return str(Path(output_dir) / "index.html")

    content = static_template.read_text(encoding='utf-8')
    content = replace_config_vars(content, config)

    import html as _html

    if site_data:
        hero = site_data.get('hero', {})
        content = content.replace('{{hero_badge}}', _html.escape(hero.get('badgeText', config.get('empresa', {}).get('categoria', ''))))
        content = content.replace('{{hero_title_1}}', _html.escape(hero.get('titleLine1', '')))
        content = content.replace('{{hero_title_2}}', _html.escape(hero.get('titleLine2', '')))
        content = content.replace('{{hero_subtitle}}', _html.escape(hero.get('subtitle', '')))
        
        services_title = site_data.get('featuresSection', {}).get('title', f"Soluções em {config.get('empresa', {}).get('categoria', '')}")
        services_subtitle = site_data.get('featuresSection', {}).get('subtitle', 'Profissionais qualificados para melhor te atender.')
        content = content.replace('{{services_title}}', _html.escape(services_title))
        content = content.replace('{{services_subtitle}}', _html.escape(services_subtitle))
        services_html = render_premium_services_html(site_data, config)
        content = content.replace('{{servicos_cards}}', services_html)
        
        authority_html = render_authority_html(site_data)
        content = content.replace('{{authority_html}}', authority_html)

        faq_html, faq_schema = render_faq_html(site_data)
        content = content.replace('{{faq_html}}', faq_html)
        content = content.replace('{{faq_schema}}', faq_schema if faq_schema else '')

        bottom_cta_html = render_bottom_cta_html(site_data, config)
        content = content.replace('{{bottom_cta_html}}', bottom_cta_html)

        # Seção Contato: título e subtítulo dinâmico da IA
        mega_cta = site_data.get('megaCtaSection', {})
        contato_titulo = mega_cta.get('title', 'Pronto para começar?')
        contato_subtitulo = mega_cta.get('subtitle', 'Entre em contato e fale com nossa equipe sem compromisso.')
        content = content.replace('{{contato_titulo}}', _html.escape(contato_titulo))
        content = content.replace('{{contato_subtitulo}}', _html.escape(contato_subtitulo))

    else:
        # Fallback de segurança se site_data estiver vazio
        from core.template_renderer import render_services_html
        content = content.replace('{{hero_badge}}', 'Referência em ' + _html.escape(config.get('empresa', {}).get('categoria', '')))
        content = content.replace('{{hero_title_1}}', _html.escape(config.get('empresa', {}).get('categoria', '')))
        content = content.replace('{{hero_title_2}}', 'com excelência')
        content = content.replace('{{hero_subtitle}}', _html.escape(f"A {config.get('empresa', {}).get('nome', '')} é referência. Serviço profissional garantido."))
        content = content.replace('{{services_title}}', _html.escape(f"Soluções em {config.get('empresa', {}).get('categoria', '')}"))
        content = content.replace('{{services_subtitle}}', 'Atendimento técnico e especializado.')
        content = content.replace('{{servicos_cards}}', render_services_html(config))
        content = content.replace('{{authority_html}}', '')
        content = content.replace('{{faq_html}}', '')
        content = content.replace('{{faq_schema}}', '')
        content = content.replace('{{bottom_cta_html}}', '')
        content = content.replace('{{contato_titulo}}', 'Fale Conosco')
        content = content.replace('{{contato_subtitulo}}', 'Solicite mais informações pelo WhatsApp.')

    # Map Guard — lê de config['empresa']['google_maps_embed'] (estrutura real do config.yaml)
    maps_url = config.get('empresa', {}).get('google_maps_embed', '').strip()
    if not maps_url:
        # fallback: tenta config['links']['googleMapsEmbed'] (caso site_data já tenha populado)
        maps_url = config.get('links', {}).get('googleMapsEmbed', '').strip()
    if maps_url:
        empresa_nome = config.get('empresa', {}).get('nome', '')
        map_html = f'<section class="map-section"><iframe src="{maps_url}" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Localização {empresa_nome}"></iframe></section>'
        content = content.replace('{{map_html}}', map_html)
    else:
        content = content.replace('{{map_html}}', '')

    residual = re.findall(r'\{\{[^}]+\}\}', content)
    if residual:
        logger.warning("Placeholders não substituídos em index_static.html: %s", residual)

    output_path = Path(output_dir) / "index.html"
    output_path.write_text(content, encoding='utf-8')
    logger.info("Home page estática gerada: %s", output_path)
    return str(output_path)
