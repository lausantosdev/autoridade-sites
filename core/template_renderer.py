"""
Template Renderer — Substitui variáveis de configuração ({{var}}) em templates HTML/CSS.

Módulo centralizado para renderização de templates com dados de config.yaml.
Utilizado pelo page_generator, generate e server para processar qualquer template estático.
"""
from datetime import datetime
from core.config_loader import get_whatsapp_link, get_phone_display
from core.utils import hex_to_rgb, slugify
from core.color_utils import ensure_text_contrast


def replace_config_vars(template: str, config: dict) -> str:
    """
    Substitui variáveis {{var}} no template com dados do config.yaml.

    Variáveis disponíveis:
        {{empresa_nome}}, {{empresa_categoria}}, {{cidade_principal}},
        {{telefone_whatsapp}}, {{telefone_display}}, {{whatsapp_link}},
        {{cor_marca}}, {{cor_marca_rgb}}, {{google_maps_url}},
        {{dominio}}, {{horario}}, {{ano}},
        {{endereco_footer}}, {{servicos_footer}}, {{locais_footer}},
        {{worker_url}}, {{client_token}}

    Args:
        template: String HTML/CSS com placeholders {{...}}
        config: Dict carregado do config.yaml

    Returns:
        Template com todos os placeholders substituídos.
    """
    empresa = config['empresa']
    r, g, b = hex_to_rgb(empresa['cor_marca'])
    theme_mode = config.get('theme', {}).get('mode', 'dark')
    color_text = ensure_text_contrast(empresa['cor_marca'], theme_mode)
    rt, gt, bt = hex_to_rgb(color_text)

    locais = config.get('seo', {}).get('locais', [])
    palavras = config.get('seo', {}).get('palavras_chave', [])
    servicos_manuais = empresa.get('servicos_manuais', [])

    # Resolver display labels: servicos_manuais com fallback para keyword
    # href usa sempre a keyword (slug real gerado), label usa o nome institucional
    def _get_display_label(idx, keyword):
        if idx < len(servicos_manuais) and servicos_manuais[idx].strip():
            return servicos_manuais[idx].strip()
        return keyword

    endereco = empresa.get('endereco', '').strip()
    endereco_footer = (
        f'<p><i class="fas fa-location-dot"></i> {endereco}</p>' if endereco else ''
    )

    cidade_principal = locais[0] if locais else ''
    if cidade_principal:
        servicos_footer = '\n'.join(
            f'<a href="{slugify(f"{p} {cidade_principal}")}.html" title="{_get_display_label(i, p)} em {cidade_principal}">{_get_display_label(i, p)}</a>'
            for i, p in enumerate(palavras)
        )
    else:
        servicos_footer = '\n'.join(
            f'<a href="mapa-do-site.html">{_get_display_label(i, p)}</a>'
            for i, p in enumerate(palavras)
        )

    categoria = empresa['categoria']
    locais_footer = '\n'.join(
        f'<p><i class="fas fa-map-marker-alt"></i> {local}</p>'
        for local in locais
    )

    replacements = {
        '{{empresa_nome}}':     empresa['nome'],
        '{{empresa_categoria}}': empresa['categoria'],
        '{{empresa_categoria_curta}}': empresa.get('categoria', '').split()[0] if empresa.get('categoria') else '',
        '{{cidade_principal}}': locais[0] if locais else '',
        '{{telefone_whatsapp}}': empresa['telefone_whatsapp'],
        '{{telefone_display}}': get_phone_display(config),
        '{{whatsapp_link}}':    get_whatsapp_link(config),
        '{{cor_marca}}':        empresa['cor_marca'],
        '{{cor_marca_rgb}}':    f"{r}, {g}, {b}",
        '{{cor_marca_text}}':   color_text,
        '{{cor_marca_text_rgb}}': f"{rt}, {gt}, {bt}",
        '{{google_maps_url}}':  empresa.get('google_maps_embed', ''),
        '{{dominio}}':          empresa['dominio'],
        '{{horario}}':          empresa.get('horario', ''),
        '{{ano}}':              str(datetime.now().year),
        '{{endereco_footer}}':  endereco_footer,
        '{{servicos_footer}}':  servicos_footer,
        '{{locais_footer}}':    locais_footer,
        '{{worker_url}}':       config.get('leads', {}).get('worker_url', ''),
        '{{client_token}}':     config.get('leads', {}).get('client_token', ''),
        '{{theme_mode}}':       config.get('theme', {}).get('mode', 'dark'),
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    return template
