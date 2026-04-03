"""
Site Data Builder — Constrói o objeto SiteData (contrato SiteGen) a partir de config + IA.

Este módulo converte os dados do config.yaml e gera conteúdo via IA
para popular a interface SiteData que o template React SiteGen espera.

Output: um dict Python compliant com a interface SiteData do SiteGen.
"""
import json
from urllib.parse import quote
from core.openrouter_client import OpenRouterClient
from core.config_loader import get_whatsapp_link, get_phone_display
from core.utils import hex_to_rgb
from datetime import datetime
from core.utils import slugify
from core.logger import get_logger
logger = get_logger(__name__)


SYSTEM_PROMPT = (
    "Você é um especialista em copywriting de alta conversão para negócios locais brasileiros. "
    "Responda apenas em JSON puro, sem markdown."
)

# Ícones Lucide disponíveis no template SiteGen (IconMapper no App.tsx)
AVAILABLE_ICONS = [
    "Zap", "Cpu", "Fingerprint", "Pencil", "Settings2", "Sparkles",
    "Shield", "Monitor", "Phone", "MapPin", "Building", "Activity",
    "Star", "Users", "HeartPulse", "Briefcase", "TrendingUp",
    "CheckCircle", "Globe", "Headphones", "PenTool", "Layout", "Database"
]


def resolve_theme_mode(config: dict, client: OpenRouterClient) -> str:
    """
    Resolve o tema (light/dark) de forma leve.
    
    Hierarquia: config.yaml > IA (chamada rápida) > fallback 'dark'.
    NÃO gera conteúdo da home — só pergunta o tema à IA.
    Propaga o resultado para config['theme']['mode'].
    """
    # 1. Config manual tem prioridade absoluta
    config_theme = config.get('theme', {}).get('mode', '')
    if config_theme in ('light', 'dark'):
        logger.info("Tema definido: %s (via config.yaml)", config_theme)
        return config_theme
    
    # 2. Pergunta rápida para a IA (~2-3 segundos)
    categoria = config['empresa']['categoria']
    logger.info("Consultando IA sobre tema ideal para: %s", categoria)
    try:
        result = client.generate_json(
            "Responda APENAS em JSON puro: {\"theme_mode\": \"light\" ou \"dark\"}",
            f"O nicho é: {categoria}. "
            "Regra: saúde/pet/infantil/alimentação/jurídico/educação/beleza/bem-estar → light. "
            "Tecnologia/automotivo/barbearia/mecânica/segurança/noturno/luxo masculino → dark. "
            "Na dúvida: público feminino/família = light, masculino/industrial = dark."
        )
        theme_mode = result.get('theme_mode', 'dark') if result else 'dark'
        if theme_mode not in ('light', 'dark'):
            theme_mode = 'dark'
    except Exception:
        theme_mode = 'dark'
    
    # 3. Propagar para config (para template_renderer usar nas subpáginas)
    if 'theme' not in config:
        config['theme'] = {}
    config['theme']['mode'] = theme_mode
    
    logger.info("Tema definido: %s (via IA)", theme_mode)
    return theme_mode


def build_site_data(config: dict, client: OpenRouterClient) -> dict:
    """
    Constrói o objeto SiteData completo.
    
    Args:
        config: Configuração do site (config.yaml parseado)
        client: OpenRouterClient para gerar conteúdo via IA
        
    Returns:
        dict compliant com a interface SiteData do SiteGen template
    """
    empresa = config['empresa']
    cor = empresa['cor_marca']
    r, g, b = hex_to_rgb(cor)
    
    palavras = config.get('seo', {}).get('palavras_chave', [])
    locais = config.get('seo', {}).get('locais', [])
    
    phone_raw = empresa['telefone_whatsapp']
    phone_display = get_phone_display(config)
    whatsapp_link = get_whatsapp_link(config)
    
    # Gerar conteúdo da home via IA
    logger.info("Gerando conteúdo da home page via IA")
    ai_content = _generate_home_content(empresa, palavras, locais, client)
    
    if not ai_content:
        logger.warning("IA retornou vazio. Usando fallbacks genéricos")
        ai_content = _fallback_content(empresa, palavras)
    
    # WhatsApp link com mensagem genérica (home page)
    msg_home = f"Olá, gostaria de saber mais sobre os serviços de {empresa['categoria']}."
    whatsapp_home = f"https://wa.me/{phone_raw}?text={quote(msg_home)}"
    cidade_principal = locais[0] if locais else ''
    categoria_nome = empresa.get('categoria', '')
    
    # Montar o objeto SiteData
    site_data = {
        "empresa": {
            "nome": empresa['nome'],
            "dominio": empresa['dominio'],
            "categoria": empresa['categoria'],
            "telefoneWhatsapp": phone_raw,
            "telefoneDisplay": phone_display,
            "horario": empresa.get('horario', ''),
            "endereco": empresa.get('endereco', ''),
            "ano": str(datetime.now().year),
        },
        
        "theme": {
            "mode": "dark",  # será sobrescrito pela lógica config > IA > fallback
            "color": cor,
            "colorRgb": f"{r}, {g}, {b}",
        },
        
        "links": {
            "whatsapp": whatsapp_link,
            "whatsappPagina": whatsapp_home,
            "telefone": f"tel:{phone_raw}",
            "googleMapsEmbed": empresa.get('google_maps_embed', ''),
        },
        
        "seo": {
            "title": ai_content.get('seo_title', f"{empresa['nome']} — {empresa['categoria']}"),
            "metaDescription": ai_content.get('seo_meta_description', f"{empresa['categoria']} profissional. {empresa['nome']}."),
            "metaKeywords": ai_content.get('seo_meta_keywords', ', '.join(palavras[:5])),
            "ogTitle": ai_content.get('seo_og_title', f"{empresa['nome']} — {empresa['categoria']}"),
            "ogDescription": ai_content.get('seo_og_description', f"{empresa['categoria']} profissional com qualidade garantida."),
            "keyword": empresa['categoria'],
            "local": locais[0] if locais else '',
        },
        
        "whatsappCtaText": "Fale Conosco",
        
        "hero": {
            "badgeText": ai_content.get('hero_badge_text', f"Referência em {empresa['categoria'].split()[0]}"),
            "badgeLinkText": "Saiba mais",
            "titleLine1": ai_content.get('hero_title_line_1', empresa['nome']),
            "titleLine2": ai_content.get('hero_title_line_2', empresa['categoria']),
            "subtitle": ai_content.get('hero_subtitle', f"{empresa['nome']} — profissionais qualificados e resultados comprovados."),
            "heroImagePath": "/hero-image.jpg",
        },
        
        # NOTA: A chave "featuresSection" é exigida pelo template React (App.tsx).
        # Semanticamente esta seção exibe SERVIÇOS, mas o React espera este key name.
        # Renomear para "servicesSection" requer rebuild do React.
        "featuresSection": {  # ← renderiza como "Serviços" na Home
            "title": ai_content.get('services_title', f"Soluções em {empresa['categoria']}"),
            "subtitle": ai_content.get('services_subtitle', "Conheça nossos serviços especializados."),
            "items": _build_services(palavras, ai_content),
        },
        
        "authoritySection": {
            "eyebrow": "SOBRE NÓS",
            "title": ai_content.get('authority_title', f"Especialistas em {empresa['categoria']}"),
            "manifestoText": ai_content.get('authority_manifesto', ''),
        },
        
        "megaCtaSection": {
            "title": ai_content.get('mega_cta_title', f"Pronto para começar?"),
            "subtitle": ai_content.get('mega_cta_subtitle', "Fale com nossa equipe pelo WhatsApp sem compromisso."),
        },
        
        "faqSection": {
            "title": "Perguntas Frequentes",
            "subtitle": "Tire suas dúvidas sobre nossos serviços",
            "categories": {"geral": "Dúvidas Gerais"},
            "faqs": {
                "geral": _build_faqs(ai_content),
            },
        },
        
        "mapSection": {
            "eyebrow": "Como Chegar",
            "title": "Nossa Localização",
            "embedUrl": empresa.get('google_maps_embed', ''),
        },
        
        "footer": {
            "descricao": ai_content.get('footer_descricao', f"{empresa['categoria']} de excelência."),
            "servicos": palavras[:6],
            "cidades": locais[:8],
            "creditoTexto": "AUTORIDADE DIGITAL",
            "creditoLink": "#",
            "slugMap": {
                "servicos": {
                    p: f"{slugify(f'{p} {cidade_principal}')}.html"
                    for p in palavras[:6]
                } if cidade_principal else {},
                "cidades": {
                    loc: f"{slugify(f'{categoria_nome} {loc}')}.html"
                    for loc in locais[:8]
                },
            },
        },
        

        
        "nav": {
            "links": [
                # href="#diferenciais" porque o React renderiza id="diferenciais" nesta seção.
                # O label "Serviços" é o que o usuário vê no menu.
                {"label": "Serviços", "href": "#diferenciais"},
                {"label": "Sobre", "href": "#sobre"},
            ],
        },
        
        "schema": {
            "localBusiness": _build_local_business_schema(
                empresa, phone_display, locais,
                description=ai_content.get('seo_meta_description', '')
            ),
            "faqPage": _build_faq_schema(ai_content),
        },
        
        "leads": {
            "workerUrl": config.get('leads', {}).get('worker_url', ''),
            "clientToken": config.get('leads', {}).get('client_token', ''),
        },
    }
    
    # Resolver tema: config.yaml > IA > fallback dark
    config_theme = config.get('theme', {}).get('mode', '')
    if config_theme in ('light', 'dark'):
        theme_mode = config_theme
    else:
        theme_mode = ai_content.get('theme_mode', 'dark')
        if theme_mode not in ('light', 'dark'):
            theme_mode = 'dark'
    
    site_data["theme"]["mode"] = theme_mode
    
    # Propagar para config (usado pelo template_renderer nas subpáginas)
    if 'theme' not in config:
        config['theme'] = {}
    config['theme']['mode'] = theme_mode
    
    logger.info("Tema definido: %s (%s)", theme_mode, 'via config.yaml' if config_theme else 'via IA')
    
    return site_data


def _generate_home_content(empresa: dict, palavras: list, locais: list, client: OpenRouterClient) -> dict:
    """Gera o conteúdo da home page via IA em uma única chamada."""
    servicos_str = ', '.join(palavras[:6]) if palavras else empresa['categoria']
    locais_str = ', '.join(locais[:4]) if locais else ''
    cidade_principal = locais[0] if locais else ''
    icons_str = ', '.join(AVAILABLE_ICONS)

    # Gerar lista numerada de serviços para o prompt
    servicos_prompt = '\n'.join(
        f'- Serviço {i}: "{s}" → service_{i}_description (máx 15 palavras), service_{i}_icon'
        for i, s in enumerate(palavras[:6], 1)
    )

    user_prompt = f"""Gere conteúdo de ALTA CONVERSÃO para a HOME PAGE da empresa '{empresa['nome']}' ({empresa['categoria']}).
Cidade principal: {cidade_principal}
Cidades atendidas: {locais_str}
Serviços: {servicos_str}

Retorne um JSON FLAT com estas chaves exatas:

SEO (cidade principal OBRIGATÓRIA em title e meta_description):
- seo_title (8-12 palavras — DEVE conter categoria + cidade principal + empresa)
- seo_meta_description (25-30 palavras — DEVE mencionar empresa, categoria e cidade principal)
- seo_meta_keywords (10 termos separados por vírgula — inclua variações com cidade)
- seo_og_title (igual ao seo_title ou variação curta)
- seo_og_description (15-20 palavras chamativas com categoria + cidade)

HERO:
- hero_badge_text (máx 3 palavras, máx 25 caracteres totais, ex: "Qualidade Premium" ou "Especialistas Locais")
- hero_title_line_1 (3-5 palavras impactantes)
- hero_title_line_2 (3-5 palavras com destaque colorido — inclui categoria ou cidade)
- hero_subtitle (20-30 palavras com empresa, categoria e cidade principal)

SERVIÇOS — Gere APENAS descrição curta e ícone para cada serviço listado:
{servicos_prompt}
Ícones — use EXATAMENTE um destes: {icons_str}

SEÇÃO SERVIÇOS (títulos da seção):
- services_title (6-10 palavras — ex: "Soluções em [categoria] em [cidade]")
- services_subtitle (8-12 palavras complementares)

AUTORIDADE (Sobre Nós — inclua messaging de confiança e diferenciais da empresa):
- authority_title (6-9 palavras — por que nos escolher)
- authority_manifesto (60-90 palavras — tom profissional, menciona cidade e categoria,
  inclua 2-3 diferenciais genéricos como atendimento personalizado e compromisso com resultado.
  NÃO invente prêmios, certificações, datas ou horários específicos.)

FAQ — 3 perguntas reais de quem busca {empresa['categoria']} em {cidade_principal}:
- faq_1_question, faq_1_answer (40-60 palavras)
- faq_2_question, faq_2_answer (40-60 palavras)
- faq_3_question, faq_3_answer (40-60 palavras)

CTA FINAL:
- mega_cta_title (4-6 palavras urgentes)
- mega_cta_subtitle (8-12 palavras complementares)

FOOTER:
- footer_descricao (10-15 palavras sobre a empresa com categoria e cidade)

TEMA VISUAL:
- theme_mode ("light" ou "dark")
  Regra: saúde, pet, infantil, alimentação, jurídico, educação, beleza feminina, bem-estar → "light"
  Tecnologia, automotivo, barbearia, mecânica, segurança, noturno, luxo masculino → "dark"
  Na dúvida: público feminino/família = light, masculino/industrial = dark

REGRAS ABSOLUTAS:
- NÃO invente prêmios, datas de fundação, horários ou números sem base
- NÃO invente capacidades específicas (certificações, atendimento 24h, etc.)
- Cidade principal '{cidade_principal}' DEVE aparecer em seo_title, seo_meta_description e hero_subtitle"""

    return client.generate_json(SYSTEM_PROMPT, user_prompt) or {}


def _build_services(palavras: list, ai_content: dict) -> list:
    """Monta a lista de cards de Serviços a partir das palavras-chave + descrições IA.
    
    Títulos vêm de config.yaml (palavras_chave), descrições e ícones da IA.
    Quantidade é dinâmica: 2, 3, 6... depende do que o operador preencheu.
    """
    services = []
    for i, keyword in enumerate(palavras[:6], 1):
        desc = ai_content.get(f'service_{i}_description', f'Serviço profissional de {keyword.lower()}.')
        icon = ai_content.get(f'service_{i}_icon', 'Zap')
        
        # Validar ícone (Lucide icon names do template React)
        if icon not in AVAILABLE_ICONS:
            icon = 'Zap'
        
        services.append({
            "title": keyword,
            "iconName": icon,
            "description": desc,
        })
    
    return services if services else [
        {"title": "Serviço Profissional", "iconName": "Shield", "description": "Atendimento de qualidade com profissionais experientes."},
    ]


def _build_faqs(ai_content: dict) -> list:
    """Monta a lista de FAQs a partir do conteúdo IA."""
    faqs = []
    for i in range(1, 4):
        q = ai_content.get(f'faq_{i}_question', '')
        a = ai_content.get(f'faq_{i}_answer', '')
        if q and a:
            faqs.append({"question": q, "answer": a})
    return faqs


def _build_local_business_schema(empresa: dict, phone_display: str, locais: list, description: str = '') -> str:
    """Gera JSON-LD para LocalBusiness."""
    location = locais[0] if locais else ''
    phone_raw = empresa.get('telefone_whatsapp', '')
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": empresa['nome'],
        "description": description or f"{empresa['nome']} — {empresa['categoria']} em {location}.",
        "telephone": phone_display,
        "url": f"https://{empresa['dominio']}/",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": location,
            "addressCountry": "BR"
        },
        "areaServed": locais[:4] if len(locais) > 1 else location,
        "openingHours": empresa.get('horario', ''),
        "sameAs": [f"https://wa.me/{phone_raw}"],
    }
    if empresa.get('endereco'):
        schema['address']['streetAddress'] = empresa['endereco']

    return json.dumps(schema, ensure_ascii=False)


def _build_faq_schema(ai_content: dict) -> str:
    """Gera JSON-LD para FAQPage."""
    entities = []
    for i in range(1, 4):
        q = ai_content.get(f'faq_{i}_question', '')
        a = ai_content.get(f'faq_{i}_answer', '')
        if q and a:
            entities.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a}
            })
    
    if not entities:
        return ''
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities
    }
    return json.dumps(schema, ensure_ascii=False)


def _fallback_content(empresa: dict, palavras: list) -> dict:
    """Conteúdo genérico caso a IA falhe."""
    fallback = {
        'hero_badge_text': f"Referência em {empresa['categoria'].split()[0]}",
        'hero_title_line_1': f"{empresa['nome']}",
        'hero_title_line_2': empresa['categoria'],
        'hero_subtitle': f"Profissionais qualificados em {empresa['categoria']}. Fale com um especialista sem compromisso.",
        'whatsapp_cta_text': 'Fale Conosco',
        'services_title': f"Soluções em {empresa['categoria']}",
        'services_subtitle': 'Conheça nossos serviços especializados.',
        'authority_title': f"Especialistas em {empresa['categoria']}",
        'authority_manifesto': f"Nossa equipe é especializada em {empresa['categoria']}. Trabalhamos com atendimento personalizado e compromisso com resultado para atender suas necessidades.",
        'mega_cta_title': 'Pronto para começar?',
        'mega_cta_subtitle': 'Fale com nossa equipe pelo WhatsApp sem compromisso.',
        'footer_descricao': f"{empresa['categoria']} de excelência. Resultados comprovados.",
    }
    # Gerar fallbacks de descrição para cada serviço
    for i, kw in enumerate(palavras[:6], 1):
        fallback[f'service_{i}_description'] = f'Serviço profissional de {kw.lower()}.'
        fallback[f'service_{i}_icon'] = 'Zap'
    return fallback
