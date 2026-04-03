"""
Page Generator - Gera páginas SEO em massa usando DeepSeek via OpenRouter
"""
import os
import json
import random
import concurrent.futures
from urllib.parse import quote
from tqdm import tqdm
import time
import threading
from core.validator import validate_page_html
from core.openrouter_client import OpenRouterClient
from core.topic_generator import get_random_mix
from core.config_loader import get_phone_display
from core.template_renderer import replace_config_vars as _replace_config_vars


# --- Retry tracking (thread-safe) ---
_retry_log = []
_retry_lock = threading.Lock()


def get_retry_log() -> list:
    """Retorna o log de retries para uso no relatório."""
    return list(_retry_log)


def _track_retry(page_title: str, attempt: int, errors: list):
    """Registra uma tentativa de retry (thread-safe)."""
    with _retry_lock:
        _retry_log.append({
            'page': page_title,
            'attempt': attempt,
            'errors': errors,
        })


# System prompt fixo (cacheado pelo DeepSeek para economia)
SYSTEM_PROMPT = "Você é um especialista em SEO de alta performance para negócios locais brasileiros. Responda apenas em JSON puro, sem markdown."


def generate_all_pages(
    pages: list,
    config: dict,
    topics: dict,
    client: OpenRouterClient,
    template_path: str,
    output_dir: str,
    progress_callback=None
):
    """
    Gera todas as páginas SEO em paralelo.
    
    Args:
        pages: Lista de dicts com 'title', 'keyword', 'location', 'filename'
        config: Configuração do site
        topics: Tópicos do nicho (palavras + frases)
        client: OpenRouterClient
        template_path: Caminho para o template HTML
        output_dir: Diretório de saída
        progress_callback: Função callback(current, total, page_title) para progresso
    """
    os.makedirs(output_dir, exist_ok=True)

    # Carregar template
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Pré-processar substituições de config (iguais para todas as páginas)
    template = _replace_config_vars(template, config)

    # Filtrar páginas já existentes
    pending = []
    for page in pages:
        output_path = os.path.join(output_dir, page['filename'])
        if os.path.exists(output_path):
            continue
        pending.append(page)

    skipped = len(pages) - len(pending)
    if skipped > 0:
        print(f"  ⏭ {skipped} páginas já existem (pulando)")

    if not pending:
        print("  ✓ Todas as páginas já foram geradas!")
        return

    print(f"  ⏳ Gerando {len(pending)} páginas com {config['api']['max_workers']} workers...")

    completed = 0
    errors = 0

    def process_page(page):
        nonlocal completed, errors
        try:
            _generate_single_page(
                page, pages, config, topics, client, template, output_dir
            )
            completed += 1
            if progress_callback:
                progress_callback(completed, len(pending), page['title'])
        except Exception as e:
            errors += 1
            _log_error(page['title'], str(e), output_dir)

    max_workers = min(config['api']['max_workers'], len(pending))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_page, p) for p in pending]

        # Progress bar para CLI
        with tqdm(total=len(pending), desc="Gerando páginas", unit="pág") as pbar:
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)

    print(f"  ✓ {completed} páginas geradas, {errors} erros")

    retry_data = get_retry_log()
    if retry_data:
        recovered = len([r for r in retry_data if r['attempt'] < config['api']['max_retries']])
        print(f"  🔄 {len(retry_data)} retries realizados ({recovered} páginas recuperadas)")


def _generate_single_page(
    page: dict, all_pages: list, config: dict, topics: dict,
    client: OpenRouterClient, template: str, output_dir: str
):
    """Gera uma única página SEO com validação e retry automático."""
    empresa = config['empresa']['nome']
    categoria = config['empresa']['categoria']
    max_retries = config['api']['max_retries']

    # Selecionar páginas aleatórias para interlinking (excluindo a atual)
    other_pages = [p for p in all_pages if p['filename'] != page['filename']]
    interlink_pool = random.sample(other_pages, min(len(other_pages), 15))
    interlink_str = "\n".join(
        f"- {p['title']} (URL: {p['filename']})" for p in interlink_pool
    )

    # Gerar mixes de tópicos para variação
    mixes = get_random_mix(topics, 6)
    mixes_str = "\n".join(f"- {m}" for m in mixes)

    last_errors = []

    for attempt in range(max_retries):
        try:
            user_prompt = f"""Gere conteúdo de ALTA CONVERSÃO + SEO para a empresa '{empresa}' ({categoria}).
Página: '{page['title']}' (keyword: '{page['keyword']}', local: '{page['location']}')

Retorne ESTRITAMENTE um JSON FLAT (nível único, sem aninhamento) com estas chaves exatas:

META TAGS:
- titulo (Título SEO: 8-12 palavras, keyword + local + empresa)
- meta_description (25-30 palavras, chamativo, com keyword + local)
- meta_keywords (10-15 termos separados por vírgula)

HERO (curto e impactante — cada linha separada, CADA UMA deve caber em UMA ÚNICA linha no celular):
- hero_titulo_linha_1 (MÁXIMO 3 palavras curtas — verbo de ação ou pergunta CURTA. Ex: "Precisa de", "Quer um novo", "Buscando o melhor". NUNCA mais de 3 palavras.)
- hero_titulo_destaque (2-4 palavras — o destaque colorido, inclui keyword)
- hero_titulo_linha_3 (2-3 palavras — fecha com local)
- hero_subtitulo (MÁXIMO 20 palavras — benefício direto + empresa + local)

DIFERENCIAIS (3 itens GENÉRICOS da empresa — NÃO são serviços):
- diferencial_1_titulo (3-5 palavras — vantagem competitiva genérica)
- diferencial_1_descricao (máx 15 palavras — frase curta explicando o diferencial)
- diferencial_1_icone (FontAwesome 6 Free Solid)
- diferencial_2_titulo, diferencial_2_descricao (máx 15 palavras), diferencial_2_icone
- diferencial_3_titulo, diferencial_3_descricao (máx 15 palavras), diferencial_3_icone
(Ícones: fas fa-headset, fas fa-medal, fas fa-check-circle, fas fa-shield-halved, fas fa-star, fas fa-thumbs-up, fas fa-handshake, fas fa-heart)
REGRA: NÃO invente capacidades específicas (atendimento 24h, ISO, certificações).
Use APENAS diferenciais universais: atendimento personalizado, equipe qualificada, compromisso com resultado, etc.

AUTORIDADE (seção "Sobre Nós"):
- autoridade_titulo (6-9 palavras — sobre a empresa + local)
- autoridade_manifesto (40-60 palavras — parágrafo profissional e honesto, sem prêmios inventados)

MEGA CTA:
- cta_titulo (4-6 palavras urgentes, inclui keyword ou local)
- cta_subtitulo (8-12 palavras, complementa o CTA)

FAQ — 3 perguntas reais de quem busca por '{page['keyword']}' em '{page['location']}':
- faq_h2 (4-6 palavras, ex: "Perguntas Frequentes Sobre [keyword]")
- faq_1_pergunta, faq_1_resposta (40-60 palavras — resposta direta e útil)
- faq_2_pergunta, faq_2_resposta (40-60 palavras — responde objeção de compra)
- faq_3_pergunta, faq_3_resposta (40-60 palavras — responde dúvida prática)

SEO EDITORIAL — 6 seções, MÍNIMO 900 palavras total:
Cada parágrafo deve ter 130-160 palavras. Conteúdo EVERGREEN — sem preços fixos, prazos ou dados que mudam.
Use keyword e local naturalmente (sem repetição forçada). Termos do nicho disponíveis: {mixes_str}
Links internos: inclua 1-2 links naturais APENAS em seo_p1 e seo_p5, usando HTML <a href="URL">texto âncora</a>.
URLs disponíveis para interlinking: {interlink_str}

- seo_h2_1 (H2 informacional: "O que é [keyword] e por que é importante em [local]", 6-10 palavras)
- seo_p1 (130-160 palavras: define o serviço, importância no contexto de [local], 1-2 links internos)

- seo_h2_2 (H2 processo: "Como funciona [keyword] profissional: etapas e técnicas", 6-10 palavras)
- seo_p2 (130-160 palavras: descreve o processo passo a passo, usa termos técnicos do nicho)

- seo_h2_3 (H2 urgência: "Quando contratar [keyword]: sinais que não devem ser ignorados", 6-10 palavras)
- seo_p3 (130-160 palavras: situações que exigem o serviço, senso de urgência sem alarmismo)

- seo_h2_4 (H2 comparação: "[keyword] profissional vs solução caseira: diferenças fundamentais", 6-10 palavras)
- seo_p4 (130-160 palavras: argumenta a favor do profissional, sem denegrir o cliente)

- seo_h2_5 (H2 autoridade local: "[empresa] em [local]: referência em [keyword]", 6-10 palavras)
- seo_p5 (130-160 palavras: autoridade da empresa, área de atendimento em [local], diferenciais, 1-2 links internos)

- seo_h2_6 (H2 ação: "Como solicitar [keyword] em [local]: simples e rápido", 6-10 palavras)
- seo_p6 (130-160 palavras: próximos passos, facilidade de contato, CTA suave, reforça localização)

REGRAS ABSOLUTAS:
- JSON FLAT: zero aninhamento, todas as chaves no nível raiz
- BREVIDADE: hero_subtitulo e beneficio_X_texto com limite rígido de palavras
- SEM ALUCINAÇÃO: não invente prêmios, certificações, datas de fundação ou números sem base
- LINKS: somente em seo_p1 e seo_p5, usando HTML puro <a href="filename.html">âncora relevante</a>
- GEO: FAQ deve responder perguntas reais que alguém faria a uma IA sobre esse serviço nessa cidade"""

            result = client.generate_json(SYSTEM_PROMPT, user_prompt)
            if not result:
                raise Exception("API retornou resposta vazia")

            # Achatar JSON aninhado (DeepSeek pode retornar estrutura aninhada)
            flat_result = _flatten_json(result)

            # Substituir placeholders do GPT no template
            html = template

            # Injetar Schema Markup (LocalBusiness + FAQPage + BreadcrumbList)
            schema = _build_schema_markup(page, config, flat_result)
            html = html.replace('{{schema_markup}}', schema)

            # Canonical URL por página
            canonical_url = f"https://{config['empresa']['dominio']}/{page['filename']}"
            html = html.replace("{{canonical_url}}", canonical_url)

            # Injetar variáveis de contexto da página primeiro
            html = html.replace("@local", page['location'])
            html = html.replace("@keyword", page['keyword'])

            # Gerar link de WhatsApp personalizado para esta página
            phone_raw = config['empresa']['telefone_whatsapp']
            msg_pagina = f"Olá, quero saber sobre {page['keyword']} em {page['location']}"
            whatsapp_pagina = f"https://wa.me/{phone_raw}?text={quote(msg_pagina)}"
            html = html.replace("@whatsapp_pagina", whatsapp_pagina)

            replaced_count = 0
            for key, value in flat_result.items():
                normalized_key = key.lower().strip()
                placeholder = f"@{normalized_key}"
                if placeholder in html:
                    html = html.replace(placeholder, str(value))
                    replaced_count += 1

            # Fallback: OG tags derivados dos campos principais
            if "@og_title" in html:
                og_title = flat_result.get('titulo', page['title'])
                html = html.replace("@og_title", str(og_title))
            if "@og_description" in html:
                og_desc = flat_result.get('meta_description', f"{page['keyword']} em {page['location']}")
                html = html.replace("@og_description", str(og_desc))

            # Injetar links internos programaticamente (garante links em seo_p1 e seo_p5)
            html = _ensure_internal_links(html, flat_result, interlink_pool)

            # VALIDAR antes de salvar
            validation = validate_page_html(page['filename'], html)

            if validation['valid']:
                # ✅ Página aprovada — salvar
                output_path = os.path.join(output_dir, page['filename'])
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                return  # Sucesso

            # ❌ Validação falhou
            last_errors = validation['errors']
            _track_retry(page['title'], attempt + 1, validation['errors'])
            print(f"    🔄 {page['filename']}: retry {attempt + 1}/{max_retries} — {validation['errors'][0]}")

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Backoff: 1s, 2s, 4s

        except Exception as e:
            last_errors = [str(e)]
            if attempt < max_retries - 1:
                _track_retry(page['title'], attempt + 1, [str(e)])
                print(f"    🔄 {page['filename']}: retry {attempt + 1}/{max_retries} — {e}")
                time.sleep(2 ** attempt)
            else:
                _track_retry(page['title'], attempt + 1, [str(e)])

    # Falhou em todas as tentativas — NÃO salvar
    raise Exception(f"Falhou após {max_retries} tentativas: {last_errors}")



def _flatten_json(data: dict, parent_key: str = '', sep: str = '_') -> dict:
    """
    Achata um JSON aninhado em chaves planas.
    Ex: {"META TAGS": {"titulo": "X"}} -> {"titulo": "X"}
    Ex: {"HERO": {"titulo_linha_1": "X"}} -> {"hero_titulo_linha_1": "X"}
    Ex: {"SEO CONTENT": {"seo_h2_1": "X"}} -> {"seo_h2_1": "X"}
    """
    items = {}
    for key, value in data.items():
        # Normalizar key: lowercase, espaços -> underscore
        norm_key = key.lower().strip().replace(' ', '_')
        new_key = f"{parent_key}{sep}{norm_key}" if parent_key else norm_key

        if isinstance(value, dict):
            items.update(_flatten_json(value, new_key, sep))
        else:
            cleaned_key = new_key

            # Remover prefixos de grupo que o DeepSeek adiciona
            for prefix in [
                'meta_tags_', 'meta_tag_', 'metatags_',
                'hero_section_', 'hero_',
                'seo_content_',
            ]:
                if cleaned_key.startswith(prefix):
                    stripped = cleaned_key[len(prefix):]
                    # Só remove se o resultado ainda faz sentido
                    if stripped and not stripped[0].isdigit():
                        # Restaura prefixos necessários
                        if prefix.startswith('hero') and not stripped.startswith('hero'):
                            stripped = 'hero_' + stripped
                        if prefix.startswith('seo_content') and not stripped.startswith('seo'):
                            stripped = 'seo_' + stripped
                        cleaned_key = stripped
                    break

            items[cleaned_key] = value
            # Manter key original como fallback
            if cleaned_key != new_key:
                items[new_key] = value

    return items


def _build_schema_markup(page: dict, config: dict, flat_result: dict) -> str:
    """
    Gera os blocos JSON-LD de Schema Markup para a página:
    - LocalBusiness: informa ao Google sobre o negócio local
    - FAQPage: expande a listagem na SERP com perguntas/respostas
    """
    empresa = config['empresa']
    phone_raw = empresa.get('telefone_whatsapp', '')
    phone_display = get_phone_display(config)
    location = page.get('location', '')
    keyword = page.get('keyword', '')

    # --- LocalBusiness ---
    local_business = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": empresa['nome'],
        "description": flat_result.get('meta_description', f"{keyword} em {location}"),
        "telephone": phone_display,
        "url": f"https://{empresa['dominio']}/{page['filename']}",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": location,
            "addressCountry": "BR"
        },
        "areaServed": location,
        "openingHours": empresa.get('horario', ''),
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": phone_raw,
            "contactType": "customer service",
            "availableLanguage": "Portuguese"
        },
        "sameAs": [
            f"https://wa.me/{phone_raw}"
        ]
    }

    # --- FAQPage (usa as perguntas já geradas pela IA) ---
    faq_entities = []
    for i in range(1, 4):
        pergunta = flat_result.get(f'faq_{i}_pergunta', '').strip()
        resposta = flat_result.get(f'faq_{i}_resposta', '').strip()
        if pergunta and resposta:
            faq_entities.append({
                "@type": "Question",
                "name": pergunta,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": resposta
                }
            })

    # --- BreadcrumbList ---
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Início",
                "item": f"https://{empresa['dominio']}/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": f"{keyword} em {location}",
                "item": f"https://{empresa['dominio']}/{page['filename']}"
            }
        ]
    }

    blocks = [
        f'<script type="application/ld+json">\n{json.dumps(local_business, ensure_ascii=False, indent=2)}\n</script>',
        f'<script type="application/ld+json">\n{json.dumps(breadcrumb, ensure_ascii=False, indent=2)}\n</script>'
    ]

    if faq_entities:
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_entities
        }
        blocks.append(
            f'<script type="application/ld+json">\n{json.dumps(faq_schema, ensure_ascii=False, indent=2)}\n</script>'
        )

    return '\n    '.join(blocks)


def _log_error(page_title: str, error: str, output_dir: str):
    """Registra erros em arquivo de log."""
    log_path = os.path.join(output_dir, '..', 'error_log.txt')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n--- ERROR: {page_title} ---\n{error}\n")


def _ensure_internal_links(html: str, flat_result: dict, interlink_pool: list) -> str:
    """
    Garante que seo_p1 e seo_p5 contenham pelo menos 1 link interno cada.
    Se a IA não incluiu links, injeta programaticamente.
    """
    if not interlink_pool:
        return html

    for field, pool_idx in [('seo_p1', 0), ('seo_p5', 5)]:
        content = flat_result.get(field, '')
        if not content or '<a href=' in content:
            continue  # Já tem link ou campo vazio
        
        link_page = interlink_pool[pool_idx % len(interlink_pool)]
        anchor = f' Conheça também nosso serviço de <a href="{link_page["filename"]}">{link_page["title"]}</a>.'
        enriched = content + anchor
        html = html.replace(content, enriched)

    return html
