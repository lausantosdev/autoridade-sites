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
    print("  🏠 Gerando conteúdo da home page via IA...")
    ai_content = _generate_home_content(empresa, palavras, locais, client)
    
    if not ai_content:
        print("  ⚠ IA retornou vazio. Usando fallbacks genéricos.")
        ai_content = _fallback_content(empresa, palavras)
    
    # WhatsApp link com mensagem genérica (home page)
    msg_home = f"Olá, gostaria de solicitar um orçamento para {empresa['categoria']}."
    whatsapp_home = f"https://wa.me/{phone_raw}?text={quote(msg_home)}"
    
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
            "mode": config.get('theme', {}).get('mode', 'dark'),
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
        
        "whatsappCtaText": ai_content.get('whatsapp_cta_text', 'Fale Conosco'),
        
        "hero": {
            "badgeText": ai_content.get('hero_badge_text', f"Referência em {empresa['categoria']}"),
            "badgeLinkText": "Saiba mais",
            "titleLine1": ai_content.get('hero_title_line_1', empresa['nome']),
            "titleLine2": ai_content.get('hero_title_line_2', empresa['categoria']),
            "subtitle": ai_content.get('hero_subtitle', f"{empresa['nome']} — profissionais qualificados e resultados comprovados."),
            "heroImagePath": "/hero-image.jpg",
        },
        
        "featuresSection": {
            "title": ai_content.get('features_title', f"Por que escolher a {empresa['nome']}?"),
            "subtitle": ai_content.get('features_subtitle', "Profissionalismo, técnica e compromisso com o resultado."),
            "items": _build_features(ai_content),
        },
        
        "authoritySection": {
            "eyebrow": "SOBRE NÓS",
            "title": ai_content.get('authority_title', f"Especialistas em {empresa['categoria']}"),
            "manifestoText": ai_content.get('authority_manifesto', ''),
        },
        
        "megaCtaSection": {
            "title": ai_content.get('mega_cta_title', f"Pronto para começar?"),
            "subtitle": ai_content.get('mega_cta_subtitle', "Orçamento rápido e sem compromisso pelo WhatsApp."),
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
        },
        
        "nav": {
            "links": [
                {"label": "Serviços", "href": "#servicos"},
                {"label": "Diferenciais", "href": "#diferenciais"},
                {"label": "Sobre", "href": "#sobre"},
            ],
        },
        
        "schema": {
            "localBusiness": _build_local_business_schema(empresa, phone_display, locais),
            "faqPage": _build_faq_schema(ai_content),
        },
        
        "leads": {
            "workerUrl": config.get('leads', {}).get('worker_url', ''),
            "clientToken": config.get('leads', {}).get('client_token', ''),
        },
    }
    
    return site_data


def _generate_home_content(empresa: dict, palavras: list, locais: list, client: OpenRouterClient) -> dict:
    """Gera o conteúdo da home page via IA em uma única chamada."""
    servicos_str = ', '.join(palavras[:6]) if palavras else empresa['categoria']
    locais_str = ', '.join(locais[:4]) if locais else ''
    icons_str = ', '.join(AVAILABLE_ICONS)
    
    user_prompt = f"""Gere conteúdo de ALTA CONVERSÃO para a HOME PAGE da empresa '{empresa['nome']}' ({empresa['categoria']}).
Serviços: {servicos_str}
Cidades atendidas: {locais_str}

Retorne um JSON FLAT com estas chaves exatas:

SEO:
- seo_title (Título SEO: 8-12 palavras)
- seo_meta_description (25-30 palavras, chamativo)
- seo_meta_keywords (10 termos separados por vírgula)
- seo_og_title
- seo_og_description

HERO:
- hero_badge_text (Frase curta de autoridade, 3-5 palavras, ex: "Referência em Limpeza de Estofados")
- hero_title_line_1 (Primeira linha do título, 3-5 palavras, impactante)
- hero_title_line_2 (Segunda linha com destaque colorido, 3-5 palavras)
- hero_subtitle (20-30 palavras descrevendo o valor da empresa)
- whatsapp_cta_text (Texto do botão WhatsApp, 2-3 palavras, ex: "Fale Conosco")

DIFERENCIAIS (6 itens):
- feature_1_title, feature_1_description, feature_1_icon
- feature_2_title, feature_2_description, feature_2_icon
- feature_3_title, feature_3_description, feature_3_icon
- feature_4_title, feature_4_description, feature_4_icon
- feature_5_title, feature_5_description, feature_5_icon
- feature_6_title, feature_6_description, feature_6_icon

Os ícones DEVEM ser um destes nomes exatos: {icons_str}

SOBRE/AUTORIDADE:
- authority_title (Título da seção sobre nós)
- authority_manifesto (Texto de 50-80 palavras, tom profissional, sem inventar prêmios ou datas)
- features_title (Título da seção de diferenciais, formato pergunta)
- features_subtitle (1 frase complementar)

FAQ (3 perguntas):
- faq_1_question, faq_1_answer
- faq_2_question, faq_2_answer
- faq_3_question, faq_3_answer

CTA FINAL:
- mega_cta_title (Frase de urgência, 4-6 palavras)
- mega_cta_subtitle (1 frase complementar)

FOOTER:
- footer_descricao (1 frase sobre a empresa, 10-15 palavras)

REGRAS:
- NÃO invente prêmios, fundação, ou números específicos
- Tom profissional e confiante
- Incluir a categoria e localização naturalmente"""

    return client.generate_json(SYSTEM_PROMPT, user_prompt) or {}


def _build_features(ai_content: dict) -> list:
    """Monta a lista de features/diferenciais a partir do conteúdo IA."""
    features = []
    for i in range(1, 7):
        title = ai_content.get(f'feature_{i}_title', '')
        desc = ai_content.get(f'feature_{i}_description', '')
        icon = ai_content.get(f'feature_{i}_icon', 'Zap')
        
        # Validar ícone
        if icon not in AVAILABLE_ICONS:
            icon = 'Zap'
        
        if title:
            features.append({
                "title": title,
                "iconName": icon,
                "description": desc,
            })
    
    return features if features else [
        {"title": "Qualidade Profissional", "iconName": "Shield", "description": "Serviço realizado com as melhores técnicas do mercado."},
        {"title": "Atendimento Rápido", "iconName": "Zap", "description": "Agilidade sem comprometer a qualidade."},
        {"title": "Orçamento Sem Compromisso", "iconName": "Briefcase", "description": "Preço justo e transparente."},
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


def _build_local_business_schema(empresa: dict, phone_display: str, locais: list) -> str:
    """Gera JSON-LD para LocalBusiness."""
    location = locais[0] if locais else ''
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": empresa['nome'],
        "description": f"{empresa['categoria']} profissional.",
        "telephone": phone_display,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": location,
            "addressCountry": "BR"
        },
        "openingHours": empresa.get('horario', ''),
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
    return {
        'hero_badge_text': f"Referência em {empresa['categoria']}",
        'hero_title_line_1': f"{empresa['nome']}",
        'hero_title_line_2': empresa['categoria'],
        'hero_subtitle': f"Profissionais qualificados em {empresa['categoria']}. Solicite seu orçamento sem compromisso.",
        'whatsapp_cta_text': 'Fale Conosco',
        'features_title': f"Por que escolher a {empresa['nome']}?",
        'features_subtitle': "Compromisso com qualidade e resultado.",
        'authority_title': f"Especialistas em {empresa['categoria']}",
        'authority_manifesto': f"Nossa equipe é especializada em {empresa['categoria']}. Trabalhamos com profissionalismo e compromisso para entregar os melhores resultados.",
        'mega_cta_title': 'Pronto para começar?',
        'mega_cta_subtitle': 'Orçamento rápido e sem compromisso pelo WhatsApp.',
        'footer_descricao': f"{empresa['categoria']} de excelência. Resultados comprovados.",
    }
