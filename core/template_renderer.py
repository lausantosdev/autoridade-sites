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

    # Montar lista de serviços para o footer:
    # Prioridade: servicos_manuais (nomes institucionais) → fallback: primeiras 6 keywords.
    if servicos_manuais:
        footer_items = [
            (servicos_manuais[i], palavras[i] if i < len(palavras) else servicos_manuais[i])
            for i in range(len(servicos_manuais))
            if servicos_manuais[i].strip()
        ]
    else:
        footer_items = [(p, p) for p in palavras[:6]]

    if cidade_principal:
        servicos_footer = '\n'.join(
            f'<a href="{slugify(f"{kw} {cidade_principal}")}.html" title="{label} em {cidade_principal}">{label}</a>'
            for label, kw in footer_items
        )
    else:
        servicos_footer = '\n'.join(
            f'<a href="mapa-do-site.html">{label}</a>'
            for label, _ in footer_items
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


def render_services_html(config: dict) -> str:
    """
    Gera o HTML estático dos cards de serviços para o placeholder {{servicos_cards}}.

    Fallback usado quando site_data não tem featuresSection.
    """
    import html as _html

    servicos_manuais = config.get('empresa', {}).get('servicos_manuais', [])
    palavras = config.get('seo', {}).get('palavras_chave', [])

    nomes = [s.strip() for s in servicos_manuais if s.strip()]
    if not nomes:
        nomes = [p for p in palavras[:6] if p]
    if not nomes:
        return ''

    icons = [
        'fas fa-star', 'fas fa-tools', 'fas fa-shield-alt',
        'fas fa-heart', 'fas fa-headset', 'fas fa-medal',
    ]

    cards = []
    for i, nome in enumerate(nomes[:6]):
        icon = icons[i % len(icons)]
        safe_nome = _html.escape(nome)
        cards.append(
            f'<div class="service-card reveal">'
            f'<div class="service-icon"><i class="{icon}" aria-hidden="true"></i></div>'
            f'<h3>{safe_nome}</h3>'
            f'</div>'
        )

    return '\n                '.join(cards)


# Mapeamento extenso de ícones Lucide (gerados pela IA) → FontAwesome
_LUCIDE_TO_FA = {
    "Sparkles": "fas fa-magic",
    "Building": "fas fa-building",
    "Building2": "fas fa-hospital",
    "Layout": "fas fa-layer-group",
    "LayoutGrid": "fas fa-th",
    "Briefcase": "fas fa-briefcase",
    "Pencil": "fas fa-pencil-alt",
    "PenTool": "fas fa-pen-nib",
    "Settings2": "fas fa-cogs",
    "Settings": "fas fa-sliders-h",
    "Shield": "fas fa-shield-alt",
    "ShieldCheck": "fas fa-shield-alt",
    "CheckCircle": "fas fa-check-circle",
    "CheckCircle2": "fas fa-check-double",
    "Check": "fas fa-check",
    "Heart": "fas fa-heart",
    "HeartPulse": "fas fa-heartbeat",
    "Activity": "fas fa-chart-line",
    "BarChart": "fas fa-chart-bar",
    "BarChart2": "fas fa-chart-bar",
    "PieChart": "fas fa-chart-pie",
    "TrendingUp": "fas fa-chart-line",
    "Home": "fas fa-home",
    "HomeIcon": "fas fa-house",
    "Users": "fas fa-users",
    "User": "fas fa-user",
    "UserCheck": "fas fa-user-check",
    "UserPlus": "fas fa-user-plus",
    "Wrench": "fas fa-wrench",
    "Tool": "fas fa-tools",
    "Scissors": "fas fa-cut",
    "Phone": "fas fa-phone",
    "PhoneCall": "fas fa-phone-alt",
    "Stethoscope": "fas fa-stethoscope",
    "Syringe": "fas fa-syringe",
    "Pill": "fas fa-pills",
    "Microscope": "fas fa-microscope",
    "Cross": "fas fa-plus",
    "Plus": "fas fa-plus",
    "PlusCircle": "fas fa-plus-circle",
    "Star": "fas fa-star",
    "Award": "fas fa-award",
    "Medal": "fas fa-medal",
    "Trophy": "fas fa-trophy",
    "Crown": "fas fa-crown",
    "Zap": "fas fa-bolt",
    "Truck": "fas fa-truck",
    "Car": "fas fa-car",
    "Clock": "fas fa-clock",
    "Calendar": "fas fa-calendar-alt",
    "CalendarCheck": "fas fa-calendar-check",
    "Camera": "fas fa-camera",
    "Image": "fas fa-image",
    "Map": "fas fa-map-marked-alt",
    "MapPin": "fas fa-map-marker-alt",
    "Search": "fas fa-search",
    "Lock": "fas fa-lock",
    "Key": "fas fa-key",
    "FileText": "fas fa-file-alt",
    "File": "fas fa-file",
    "Folder": "fas fa-folder",
    "Package": "fas fa-box",
    "ShoppingCart": "fas fa-shopping-cart",
    "ShoppingBag": "fas fa-shopping-bag",
    "Tag": "fas fa-tag",
    "Gift": "fas fa-gift",
    "Leaf": "fas fa-leaf",
    "Sun": "fas fa-sun",
    "Moon": "fas fa-moon",
    "Droplets": "fas fa-tint",
    "Droplet": "fas fa-tint",
    "Flame": "fas fa-fire",
    "Wind": "fas fa-wind",
    "Thermometer": "fas fa-thermometer-half",
    "Wifi": "fas fa-wifi",
    "Cpu": "fas fa-microchip",
    "Monitor": "fas fa-desktop",
    "Laptop": "fas fa-laptop",
    "Smartphone": "fas fa-mobile-alt",
    "Headphones": "fas fa-headphones",
    "Music": "fas fa-music",
    "Video": "fas fa-video",
    "Tv": "fas fa-tv",
    "Globe": "fas fa-globe",
    "Link": "fas fa-link",
    "Send": "fas fa-paper-plane",
    "MessageCircle": "fas fa-comment",
    "MessageSquare": "fas fa-comments",
    "Mail": "fas fa-envelope",
    "Bell": "fas fa-bell",
    "Info": "fas fa-info-circle",
    "HelpCircle": "fas fa-question-circle",
    "AlertCircle": "fas fa-exclamation-circle",
    "Edit": "fas fa-edit",
    "Eye": "fas fa-eye",
    "Headset": "fas fa-headset",
    "LifeBuoy": "fas fa-life-ring",
    "DollarSign": "fas fa-dollar-sign",
    "CreditCard": "fas fa-credit-card",
    "Banknote": "fas fa-money-bill-wave",
    "Percent": "fas fa-percent",
    "Baby": "fas fa-baby",
    "Dog": "fas fa-dog",
    "Cat": "fas fa-cat",
    "Fish": "fas fa-fish",
    "Bird": "fas fa-dove",
    "Paw": "fas fa-paw",
    "Bone": "fas fa-bone",
    "Scissors2": "fas fa-cut",
    "Bath": "fas fa-bath",
    "Soap": "fas fa-pump-soap",
    "SprayCan": "fas fa-spray-can",
    "Bug": "fas fa-bug",
    "Biohazard": "fas fa-biohazard",
    "FlaskConical": "fas fa-flask",
    "Flask": "fas fa-flask",
    "Dumbbell": "fas fa-dumbbell",
    "Accessibility": "fas fa-wheelchair",
    "Ambulance": "fas fa-ambulance",
    "Bandage": "fas fa-band-aid",
    "Clipboard": "fas fa-clipboard",
    "ClipboardCheck": "fas fa-clipboard-check",
    "BookOpen": "fas fa-book-open",
    "Book": "fas fa-book",
    "GraduationCap": "fas fa-graduation-cap",
    "Lightbulb": "fas fa-lightbulb",
    "Coffee": "fas fa-coffee",
    "Utensils": "fas fa-utensils",
    "Recycle": "fas fa-recycle",
    "Sprout": "fas fa-seedling",
    "Trees": "fas fa-tree",
    "Mountain": "fas fa-mountain",
    "Waves": "fas fa-water",
    "Fingerprint": "fas fa-fingerprint",
    "Scan": "fas fa-barcode",
    "QrCode": "fas fa-qrcode",
    "Printer": "fas fa-print",
    "Brush": "fas fa-paint-brush",
    "Palette": "fas fa-palette",
}

# Fallback cíclico — variado, nunca só checkmarks
_FALLBACK_ICONS = [
    "fas fa-star", "fas fa-shield-alt", "fas fa-heart",
    "fas fa-award", "fas fa-bolt", "fas fa-medal",
    "fas fa-users", "fas fa-clock", "fas fa-magic",
]


def render_premium_services_html(site_data: dict, config: dict) -> str:
    """Renderiza cards de serviços ricos com dados da IA (featuresSection)."""
    import html as _html

    items = site_data.get("featuresSection", {}).get("items", [])
    if not items:
        return render_services_html(config)

    cards = []
    for i, item in enumerate(items):
        lucide_icon = item.get("iconName", "")
        icon = _LUCIDE_TO_FA.get(lucide_icon, _FALLBACK_ICONS[i % len(_FALLBACK_ICONS)])

        # Preserva o título exatamente como a IA gerou — sem str.title() que quebra
        title = item.get("title", "")
        desc = item.get("description", "")
        safe_title = _html.escape(title)
        safe_desc = _html.escape(desc)

        cards.append(
            f'<div class="premium-service-card reveal">'
            f'<div class="service-icon"><i class="{icon}" aria-hidden="true"></i></div>'
            f'<div class="service-content">'
            f'<h3>{safe_title}</h3>'
            f'<p>{safe_desc}</p>'
            f'</div>'
            f'</div>'
        )

    return "\n                ".join(cards)


def render_faq_html(site_data: dict) -> tuple:
    """Renderiza seção FAQ com accordion CSS nativo (sem details/summary) e JSON-LD."""
    import html as _html
    import json

    faqs = site_data.get("faqSection", {}).get("faqs", {}).get("geral", [])
    if not faqs:
        return "", ""

    html_out = '<section id="faq" class="section section-alt">\n'
    html_out += '<div class="container">\n'
    html_out += '<div class="section-header reveal">\n'
    html_out += '<span class="section-tag">D\u00favidas Frequentes</span>\n'
    html_out += '<h2 class="section-title">Perguntas Frequentes</h2>\n'
    html_out += '<p class="section-subtitle">Tire suas d\u00favidas sobre nossos servi\u00e7os e atendimento.</p>\n'
    html_out += '</div>\n'
    html_out += '<div class="faq-accordion reveal">\n'

    schema_entities = []

    for idx, faq in enumerate(faqs):
        q = faq.get("question", "")
        a = faq.get("answer", "")
        item_id = f"faq-{idx}"

        html_out += f'<div class="faq-item" id="{item_id}">\n'
        html_out += (
            f'<button class="faq-btn" aria-expanded="false" '
            f'aria-controls="{item_id}-ans" onclick="toggleFaq(this)">'
            f'<span class="faq-q">{_html.escape(q)}</span>'
            f'<svg class="faq-chevron" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2.5" aria-hidden="true">'
            f'<polyline points="6 9 12 15 18 9"/></svg>'
            f'</button>\n'
        )
        html_out += (
            f'<div class="faq-ans" id="{item_id}-ans" aria-hidden="true">'
            f'<p>{_html.escape(a)}</p>'
            f'</div>\n'
        )
        html_out += '</div>\n'

        schema_entities.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a
            }
        })

    html_out += '</div>\n</div>\n</section>'
    html_out += """
<script>
function toggleFaq(btn){
    var item=btn.closest('.faq-item');
    var ans=item.querySelector('.faq-ans');
    var isOpen=btn.getAttribute('aria-expanded')==='true';
    document.querySelectorAll('.faq-item').forEach(function(el){
        el.querySelector('.faq-btn').setAttribute('aria-expanded','false');
        el.querySelector('.faq-ans').setAttribute('aria-hidden','true');
        el.classList.remove('open');
    });
    if(!isOpen){
        btn.setAttribute('aria-expanded','true');
        ans.setAttribute('aria-hidden','false');
        item.classList.add('open');
    }
}
</script>"""

    schema_json = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": schema_entities
    }
    schema_str = f'<script type="application/ld+json">\n{json.dumps(schema_json, indent=2, ensure_ascii=False)}\n</script>'

    return html_out, schema_str


def render_authority_html(site_data: dict) -> str:
    """Renderiza seção Sobre Nós / Manifesto de Autoridade a partir dos dados da IA.

    Estrutura visual alinhada com o React:
    - .sobre-section: padding responsivo (56px/128px) + border-top + overflow-hidden
    - .sobre-blob: blob decorativo radial com a cor da marca
    - .sobre-container: max-w-4xl (896px) — mais estreito que o .container padrão
    - .sobre-manifesto: texto solto sem card/box-shadow (sem .premium-authority)
    """
    import html as _html

    authority = site_data.get("authoritySection", {})
    manifesto = authority.get("manifestoText", "")
    title = authority.get("title", "Nossa História e Responsabilidade")
    eyebrow = authority.get("eyebrow", "SOBRE NÓS")

    if not manifesto:
        return ""

    paragraphs = [p.strip() for p in manifesto.split("\n") if p.strip()]
    p_html = "".join(f"<p>{_html.escape(p)}</p>" for p in paragraphs)

    html_out  = '<section id="sobre" class="sobre-section">\n'
    html_out += '    <div class="sobre-blob" aria-hidden="true"></div>\n'
    html_out += '    <div class="container sobre-container">\n'
    html_out += '        <div class="section-header reveal">\n'
    html_out += f'            <span class="section-tag">{_html.escape(eyebrow)}</span>\n'
    html_out += f'            <h2 class="section-title">{_html.escape(title)}</h2>\n'
    html_out += '        </div>\n'
    html_out += f'        <div class="sobre-manifesto reveal">\n            {p_html}\n        </div>\n'
    html_out += '    </div>\n</section>'

    return html_out



def render_bottom_cta_html(site_data: dict, config: dict) -> str:
    """Renderiza Banner CTA de Fechamento com botão laranja funcional apontando para WhatsApp."""
    import html as _html

    nome = config.get("empresa", {}).get("nome", "")
    cat = config.get("empresa", {}).get("categoria", "")
    whatsapp = get_whatsapp_link(config)

    cta = site_data.get("bottomCta", {})
    cta_text = cta.get(
        "bodyText",
        f"{nome} \u2014 refer\u00eancia em {cat}. Solicite um or\u00e7amento sem compromisso."
    )
    cta_btn = cta.get("ctaButtonText", "Falar pelo WhatsApp")

    safe_text = _html.escape(cta_text)
    safe_btn = _html.escape(cta_btn)

    html_out = '<section id="bottom-cta" class="bottom-cta-section">\n'
    html_out += '<div class="container">\n'
    html_out += '<div class="bottom-cta-inner reveal">\n'
    html_out += f'<p class="bottom-cta-text">{safe_text}</p>\n'
    html_out += (
        f'<a href="{whatsapp}" class="btn btn-primary bottom-cta-btn" '
        f'target="_blank" rel="noopener noreferrer">'
        f'<i class="fab fa-whatsapp"></i> {safe_btn}'
        f'</a>\n'
    )
    html_out += '</div>\n'
    html_out += '</div>\n</section>'

    return html_out
