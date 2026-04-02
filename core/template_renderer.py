"""
Template Renderer — Substitui variáveis de configuração ({{var}}) em templates HTML/CSS.

Módulo centralizado para renderização de templates com dados de config.yaml.
Utilizado pelo page_generator, generate e server para processar qualquer template estático.
"""
from datetime import datetime
from core.config_loader import get_whatsapp_link, get_phone_display
from core.utils import hex_to_rgb, slugify


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

    locais = config.get('seo', {}).get('locais', [])
    palavras = config.get('seo', {}).get('palavras_chave', [])

    endereco = empresa.get('endereco', '').strip()
    endereco_footer = (
        f'<p><i class="fas fa-location-dot"></i> {endereco}</p>' if endereco else ''
    )

    cidade_principal = locais[0] if locais else ''
    if cidade_principal:
        servicos_footer = '\n'.join(
            f'<a href="{slugify(f"{p} {cidade_principal}")}.html" title="{p} em {cidade_principal}">{p}</a>'
            for p in palavras
        )
    else:
        servicos_footer = '\n'.join(
            f'<a href="mapa-do-site.html">{p}</a>' for p in palavras
        )

    categoria = empresa['categoria']
    locais_footer = '\n'.join(
        f'<a href="{slugify(f"{categoria} {local}")}.html" title="{categoria} em {local}"><i class="fas fa-map-marker-alt"></i> {local}</a>'
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
