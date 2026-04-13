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
from core.color_utils import ensure_text_contrast
from datetime import datetime
from core.utils import slugify
from core.page_generator import _flatten_json
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


def _resolve_display_names(servicos_manuais: list, palavras_chave: list) -> list:
    """
    Resolve os rótulos visuais para os cards de Serviços e o Footer.

    Estratégia de prioridade:
    1. Se servicos_manuais estiver preenchido, usa SOMENTE eles (sem misturar keywords).
       Isso evita que cards extras mostrem palavras-chave SEO ao lado de nomes institucionais.
    2. Se servicos_manuais estiver vazio, usa palavras_chave como fallback (comportamento legado).

    Returns:
        list: Lista de strings com os display names (máximo 6).
    """
    if servicos_manuais:
        # Usuário preencheu nomes institucionais → usa apenas eles, sem completar com keywords
        clean = [s.strip() for s in servicos_manuais[:6] if s.strip()]
        if clean:
            return clean
    # Fallback: nenhum serviço manual → usa palavras-chave como labels
    return [kw for kw in palavras_chave[:6]]


def _compute_regiao_ampla(locais: list) -> str:
    """
    Deriva a 'região ampla' a partir da lista de áreas atendidas.
    Funciona tanto para bairros quanto para cidades.

    Exemplos:
        ["Vila Industrial"]                  → "Vila Industrial e Região"
        ["Moema", "Pinheiros", "Santana"]    → "Moema, Pinheiros e Região"
        ["Curitiba", "São José dos Pinhais"] → "Curitiba e Região"
        []                                   → ''
    """
    if not locais:
        return ''
    if len(locais) == 1:
        return f"{locais[0]} e Região"
    return f"{locais[0]}, {locais[1]} e Região"


def resolve_theme_mode(config: dict, client: OpenRouterClient) -> str:
    """
    Resolve o tema (light/dark) de forma leve.
    
    Hierarquia: config.yaml > IA (chamada rápida) > fallback 'dark'.
    NÃO gera conteúdo da home — só pergunta o tema à IA.
    Propaga o resultado para config['theme']['mode'].
    """
    # 1. Config manual tem prioridade absoluta
    config_theme = config.get('theme', {}).get('mode', 'auto')
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
        theme_mode = result.get('theme_mode', 'light') if result else 'light'
        if theme_mode not in ('light', 'dark'):
            theme_mode = 'light'
    except Exception:
        theme_mode = 'light'
    
    # 3. Propagar para config (para template_renderer usar nas subpáginas)
    if 'theme' not in config:
        config['theme'] = {}
    config['theme']['mode'] = theme_mode
    
    logger.info("Tema definido: %s (via IA)", theme_mode)
    return theme_mode


def build_site_data(config: dict, client: OpenRouterClient = None, gemini_client=None, raw_ai_override: dict = None) -> dict:
    """
    Constrói o objeto SiteData completo.

    Args:
        config: Configuração do site (config.yaml parseado)
        client: OpenRouterClient (fallback para a home)
        gemini_client: GeminiClient opcional (primário para a home)
        raw_ai_override: Opcional. Se passado, bypassa a IA e usa este JSON estruturado (útil para fast sync).

    Returns:
        dict compliant com a interface SiteData do SiteGen template
    """
    empresa = config['empresa']
    cor = empresa['cor_marca']
    r, g, b = hex_to_rgb(cor)

    palavras = config.get('seo', {}).get('palavras_chave', [])
    locais = config.get('seo', {}).get('locais', [])
    servicos_manuais = config.get('empresa', {}).get('servicos_manuais', [])
    # display_names: rótulos visuais para cards e footer (desacoplados das keywords)
    display_names = _resolve_display_names(servicos_manuais, palavras)

    phone_raw = empresa['telefone_whatsapp']
    phone_display = get_phone_display(config)
    whatsapp_link = get_whatsapp_link(config)

    if raw_ai_override:
        logger.info("Usando raw_ai_override para a home page (bypass de IA)")
        ai_content = raw_ai_override
    else:
        # Gerar conteúdo da home via IA (Gemini → OpenAI → fallback genérico)
        logger.info("Gerando conteúdo da home page via IA")
        ai_content = _generate_home_content(empresa, palavras, locais, client, gemini_client)
        
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
            "mode": theme_mode if 'theme_mode' in locals() else "light",  # será sobrescrito pela lógica config > IA > fallback
            "color": cor,
            "colorRgb": f"{r}, {g}, {b}",
            "colorText": cor,  # será sobrescrito após resolver o tema
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
            "heroImagePath": "./hero-image.webp",
        },
        
        # NOTA: A chave "featuresSection" é exigida pelo template React (App.tsx).
        # Semanticamente esta seção exibe SERVIÇOS, mas o React espera este key name.
        # Renomear para "servicesSection" requer rebuild do React.
        "featuresSection": {  # ← renderiza como "Serviços" na Home
            "title": ai_content.get('services_title', f"Soluções em {empresa['categoria']}"),
            "subtitle": ai_content.get('services_subtitle', "Conheça nossos serviços especializados."),
            "items": _build_services(palavras, ai_content, display_names),
        },
        
        "authoritySection": {
            "eyebrow": "SOBRE NÓS",
            "title": (
                ai_content.get('authority_title')
                or ai_content.get('autoridade_titulo')
                or f"Especialistas em {empresa['categoria']}"
            ),
            "manifestoText": (
                ai_content.get('authority_manifesto')
                or ai_content.get('autoridade_manifesto')
                or ai_content.get('manifesto')
                or ''
            ),
        },
        
        "megaCtaSection": {
            "title": "Fale Conosco",
            "subtitle": "Solicite mais informações pelo WhatsApp.",
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
            "servicos": display_names,
            "cidades": locais[:8],
            "creditoTexto": "AUTORIDADE DIGITAL",
            "creditoLink": "#",
            "slugMap": {
                "servicos": (
                    {
                        # Chave primária: keyword → slug (mantém compatibilidade existente)
                        **{p: f"{slugify(f'{p} {cidade_principal}')}.html" for p in palavras[:6]},
                        # Alias: display_name → mesmo slug (para linkifyFooter encontrar pelo texto visível)
                        # Só inclui quando display_name difere da keyword (evita entradas duplicadas)
                        **{
                            display_names[i]: f"{slugify(f'{palavras[i]} {cidade_principal}')}.html"
                            for i in range(min(len(palavras[:6]), len(display_names)))
                            if display_names[i] != palavras[i]
                        }
                    }
                ) if cidade_principal else {},
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
        
        "_raw_ai": ai_content,  # Guarda para cache
    }
    
    # Resolver tema: config.yaml > IA > fallback light
    config_theme = config.get('theme', {}).get('mode', 'auto')
    if config_theme in ('light', 'dark'):
        theme_mode = config_theme
    else:
        theme_mode = ai_content.get('theme_mode', 'light')
        if theme_mode not in ('light', 'dark'):
            theme_mode = 'light'
    
    site_data["theme"]["mode"] = theme_mode

    # Derivar colorText: versão da cor ajustada para garantir WCAG AA como texto
    color_text = ensure_text_contrast(cor, theme_mode)
    site_data["theme"]["colorText"] = color_text
    if color_text != cor:
        logger.info("Cor ajustada para contraste WCAG AA: %s → %s (tema %s)", cor, color_text, theme_mode)

    # Propagar para config (usado pelo template_renderer nas subpáginas)
    if 'theme' not in config:
        config['theme'] = {}
    config['theme']['mode'] = theme_mode

    logger.info("Tema definido: %s (%s)", theme_mode, 'via config.yaml' if config_theme else 'via IA')
    
    return site_data


def _generate_home_content(empresa: dict, palavras: list, locais: list, client: OpenRouterClient, gemini_client=None) -> dict:
    """
    Gera o conteúdo da home page via IA (Gemini → OpenAI fallback).

    Arquitetura HUB & SPOKE:
    A Home é o HUB — fala da marca e da categoria em sentido amplo.
    Subpáginas são os SPOKES — cada uma reivindica um par keyword + localidade.
    O H1/hero da Home NUNCA deve estar amarrado a um bairro ou cidade específica,
    pois isso causaria canibalismo de palavras-chave contra as próprias subpáginas.
    """
    servicos_str = ', '.join(palavras[:6]) if palavras else empresa['categoria']
    locais_str = ', '.join(locais[:6]) if locais else ''
    regiao_ampla = _compute_regiao_ampla(locais)
    icons_str = ', '.join(AVAILABLE_ICONS)

    # Gerar lista numerada de serviços para o prompt
    servicos_prompt = '\n'.join(
        f'- Serviço {i}: "{s}" → service_{i}_description (máx 15 palavras), service_{i}_icon'
        for i, s in enumerate(palavras[:6], 1)
    )

    user_prompt = f"""Gere conteúdo de ALTA CONVERSÃO para a HOME PAGE da empresa '{empresa['nome']}' ({empresa['categoria']}).
Região de atuação: {regiao_ampla}
Áreas atendidas (para contexto): {locais_str}
Serviços: {servicos_str}

Retorne um JSON FLAT com estas chaves exatas:

SEO (foco na MARCA e CATEGORIA — sem travar em área específica):
- seo_title (8-12 palavras — padrão: "{empresa['nome']} — [categoria] | {regiao_ampla}". Posiciona a empresa como referência regional, não local de bairro)
- seo_meta_description (25-30 palavras — menciona empresa, categoria e cobertura regional. Ex: "A [empresa] oferece [categoria] de qualidade em {regiao_ampla}. Atendimento personalizado e resultados comprovados.")
- seo_meta_keywords (10 termos separados por vírgula — misture categoria + variações de serviços, sem focar em um bairro só)
- seo_og_title (igual ao seo_title ou variação curta)
- seo_og_description (15-20 palavras chamativas com categoria + cobertura ampla)

HERO — REGRA CRÍTICA DE SEO: a Home é o HUB de autoridade da marca. O hero NUNCA deve citar um bairro/cidade específico no badge ou no título, pois isso canibaliza as subpáginas. Foque em POSICIONAMENTO DE MARCA e no DESEJO DO CLIENTE:
- hero_badge_text (máx 4 palavras — foca em CATEGORIA ou POSICIONAMENTO. Ex: "Mecânica de Confiança", "Petshop Especializado", "Clínica Veterinária Premium". PROIBIDO: incluir nome de bairro ou cidade)
- hero_title_line_1 (3-5 palavras — fala do DESEJO DO CLIENTE, não da empresa. Ex: "Seu Pet Merece", "Procurando um bom", "Cansado de problemas com". PROIBIDO: "Cuidados de Alto Nível", "Soluções Completas", frases institucionais)
- hero_title_line_2 (3-5 palavras com destaque colorido — complementa linha_1 com a CATEGORIA ou BENEFÍCIO CENTRAL. PROIBIDO: bairro ou cidade específico. Ex: "Atendimento Veterinário?", "Mecânico Confiável?", "Assessoria Jurídica?")
- hero_subtitle (10-15 palavras no MÁXIMO. Frase direta sobre a empresa e a CATEGORIA — PROIBIDO citar bairro, cidade ou região. Foque em posicionamento de marca e benefício central. Ex: "A {empresa['nome']} é referência em {empresa['categoria']} com qualidade e compromisso.")

SERVIÇOS — Gere APENAS descrição curta e ícone para cada serviço listado:
{servicos_prompt}
Ícones — use EXATAMENTE um destes: {icons_str}

SEÇÃO SERVIÇOS (títulos da seção):
- services_title (6-10 palavras — ex: "Soluções em {empresa['categoria']} para Toda a Região")
- services_subtitle (8-12 palavras complementares, sem geo-lock)

AUTORIDADE (Sobre Nós — inclua messaging de confiança e diferenciais da empresa):
- authority_title (6-9 palavras — por que nos escolher, foco na marca)
- authority_manifesto (60-90 palavras — tom profissional, menciona a cobertura regional ({regiao_ampla}),
  inclua 2-3 diferenciais genéricos como atendimento personalizado e compromisso com resultado.
  NÃO invente prêmios, certificações, datas ou horários específicos.)

FAQ — 3 perguntas GERAIS de quem busca {empresa['categoria']} (sem amarrar a cidade específica):
- faq_1_question, faq_1_answer (40-60 palavras — pergunta sobre o serviço/processo geral)
- faq_2_question, faq_2_answer (40-60 palavras — responde objeção de compra/contratação)
- faq_3_question, faq_3_answer (40-60 palavras — pergunta sobre cobertura ou forma de contato)

CTA FINAL:
- mega_cta_title (4-6 palavras urgentes — sem geo-lock)
- mega_cta_subtitle (8-12 palavras complementares)

FOOTER:
- footer_descricao (10-15 palavras — empresa + categoria + cobertura. Ex: "{empresa['nome']}: {empresa['categoria']} de excelência em {regiao_ampla}.")

TEMA VISUAL:
- theme_mode ("light" ou "dark")
  Regra: saúde, pet, infantil, alimentação, jurídico, educação, beleza feminina, bem-estar → "light"
  Tecnologia, automotivo, barbearia, mecânica, segurança, noturno, luxo masculino → "dark"
  Na dúvida: público feminino/família = light, masculino/industrial = dark

REGRAS ABSOLUTAS:
- NÃO invente prêmios, datas de fundação, horários ou números sem base
- NÃO invente capacidades específicas (certificações, atendimento 24h, etc.)
- NUNCA coloque nome de bairro ou cidade específicos no hero_badge_text, hero_title_line_1 ou hero_title_line_2
- A Home é o HUB de MARCA — as subpáginas cuidam do SEO local por bairro/cidade"""

    # Mesmo padrão das subpáginas: Gemini → OpenAI fallback
    raw = None
    if gemini_client:
        raw = gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
        if not raw:
            logger.warning("Home: Gemini falhou — acionando OpenAI fallback")
    if not raw:
        raw = client.generate_json(SYSTEM_PROMPT, user_prompt)
    return _flatten_json(raw or {})


def _build_services(palavras: list, ai_content: dict, display_names: list = None) -> list:
    """Monta a lista de cards de Serviços a partir de display_names + descrições IA.

    Iteração baseada em display_names (não em palavras_chave), eliminando a causa
    de keywords aparecerem como títulos quando o usuário preencheu serviços manuais.
    Descrições e ícones vêm da IA, indexados pela posição correspondente na keyword list.
    """
    if display_names is None:
        display_names = palavras

    services = []
    for i, display_label in enumerate(display_names[:6], 1):
        # Keyword na mesma posição (para lookup das descrições geradas pela IA)
        keyword = palavras[i - 1] if i - 1 < len(palavras) else display_label

        desc = ai_content.get(f'service_{i}_description', f'Serviço profissional de {keyword.lower()}.')
        icon = ai_content.get(f'service_{i}_icon', 'Zap')

        # Validar ícone (Lucide icon names do template React)
        if icon not in AVAILABLE_ICONS:
            icon = 'Zap'

        services.append({
            "title": display_label,   # nome institucional (nunca keyword)
            "iconName": icon,
            "description": desc,
        })

    return services if services else [
        {"title": "Serviço Profissional", "iconName": "Shield", "description": "Atendimento de qualidade com profissionais experientes."},
    ]


def _build_faqs(ai_content: dict) -> list:
    """Monta a lista de FAQs a partir do conteúdo IA.
    
    Suporta aliases inglês/português para tolerar variações de resposta da IA.
    """
    faqs = []
    for i in range(1, 4):
        q = (
            ai_content.get(f'faq_{i}_question')
            or ai_content.get(f'faq_{i}_pergunta')
        )
        a = (
            ai_content.get(f'faq_{i}_answer')
            or ai_content.get(f'faq_{i}_resposta')
        )
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
    """Gera JSON-LD para FAQPage.
    
    Suporta aliases inglês/português — alinhado com _build_faqs().
    """
    entities = []
    for i in range(1, 4):
        q = (
            ai_content.get(f'faq_{i}_question')
            or ai_content.get(f'faq_{i}_pergunta', '')
        )
        a = (
            ai_content.get(f'faq_{i}_answer')
            or ai_content.get(f'faq_{i}_resposta', '')
        )
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
    categoria = empresa['categoria']
    fallback = {
        'hero_badge_text': f"{empresa['categoria'].split()[0]} em {palavras[0] if palavras else empresa['categoria']}",
        'hero_title_line_1': f"Procurando {empresa['categoria'].split()[0]}",
        'hero_title_line_2': f"em {empresa.get('endereco', empresa['nome'])}?",
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

    # NOVO: FAQs genéricos para garantir que a seção nunca fique vazia
    faq_fallbacks = [
        (
            f"Como funciona o serviço de {categoria}?",
            f"Nosso processo de {categoria} é realizado por profissionais "
            f"qualificados com foco em qualidade e agilidade. "
            f"Entre em contato pelo WhatsApp para mais detalhes sobre o seu caso específico."
        ),
        (
            "Como solicito um orçamento?",
            f"O orçamento é gratuito e sem compromisso. "
            f"Basta entrar em contato pelo WhatsApp informando sua necessidade. "
            f"Nossa equipe retornará rapidamente com as opções disponíveis."
        ),
        (
            "Qual o prazo para realização do serviço?",
            f"O prazo varia conforme o tipo e a complexidade do serviço de {categoria}. "
            f"Após a avaliação inicial, informamos o tempo estimado com clareza e transparência. "
            f"Trabalhamos para atender com agilidade sem comprometer a qualidade."
        ),
    ]
    for i, (q, a) in enumerate(faq_fallbacks, 1):
        fallback[f'faq_{i}_question'] = q
        fallback[f'faq_{i}_answer']   = a

    return fallback
