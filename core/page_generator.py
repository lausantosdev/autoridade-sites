"""
Page Generator - Gera páginas SEO em massa usando DeepSeek via OpenRouter
"""
import os
import random
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
from core.openrouter_client import OpenRouterClient
from core.topic_generator import get_random_mix
from core.config_loader import get_whatsapp_link, get_phone_display
from core.utils import hex_to_rgb


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


def _generate_single_page(
    page: dict, all_pages: list, config: dict, topics: dict,
    client: OpenRouterClient, template: str, output_dir: str
):
    """Gera uma única página SEO."""
    empresa = config['empresa']['nome']
    categoria = config['empresa']['categoria']

    # Selecionar páginas aleatórias para interlinking (excluindo a atual)
    other_pages = [p for p in all_pages if p['filename'] != page['filename']]
    interlink_pool = random.sample(other_pages, min(len(other_pages), 15))
    interlink_str = "\n".join(
        f"- {p['title']} (URL: {p['filename']})" for p in interlink_pool
    )

    # Gerar mixes de tópicos para variação
    mixes = get_random_mix(topics, 6)
    mixes_str = "\n".join(f"- {m}" for m in mixes)

    user_prompt = f"""Gere conteúdo Estratégico de ALTA CONVERSÃO + SEO para a empresa '{empresa}' ({categoria}).
Página: '{page['title']}' (keyword: '{page['keyword']}', local: '{page['location']}')

Retorne ESTRITAMENTE um JSON FLAT (nível único, sem aninhamento) com estas chaves exatas:

- titulo (Título SEO: 8-12 palavras, incluir keyword e local)
- meta_description (Meta description chamativa: 25-30 palavras)
- meta_keywords (10-15 termos separados por vírgula)

- hero_titulo_linha_1
- hero_titulo_destaque
- hero_titulo_linha_3
- hero_subtitulo (20-30 palavras)

- dor_h2 (Título provocativo)
- dor_p1, dor_p2 (80-100 palavras cada)

- beneficio_1_titulo, beneficio_1_texto, beneficio_1_icone (Use classes REAIS do FontAwesome 6, ex: fas fa-clock, fas fa-shield-halved, fas fa-truck-fast, fas fa-tools)
- beneficio_2_titulo, beneficio_2_texto, beneficio_2_icone
- beneficio_3_titulo, beneficio_3_texto, beneficio_3_icone
- beneficio_4_titulo, beneficio_4_texto, beneficio_4_icone

- processo_h2 (Título técnico)
- processo_p1, processo_p2 (120-150 palavras cada, rico em SEO técnico)

- autoridade_h2
- autoridade_p1, autoridade_p2 (100-120 palavras cada)

- faq_h2
- faq_1_pergunta, faq_1_resposta
- faq_2_pergunta, faq_2_resposta
- faq_3_pergunta, faq_3_resposta

REGRAS CRÍTICAS:
- VOLUME DE TEXTO: O total de texto deve ultrapassar 1000 palavras para SEO.
- DENSIDADE: Insira a keyword e o local '{page['location']}' naturalmente em todos os blocos.
- TECNICIDADE: Use termos técnicos reais do nicho: {mixes_str}
- LINKS: Incorpore estes links internos no texto: {interlink_str}
- SEM ALUCINAÇÃO: Não invente prêmios ou datas de fundação. Use tom profissional."""

    result = client.generate_json(SYSTEM_PROMPT, user_prompt)
    if not result:
        raise Exception("API retornou resposta vazia")

    # Achatar JSON aninhado (DeepSeek pode retornar estrutura aninhada)
    flat_result = _flatten_json(result)

    # Substituir placeholders do GPT no template
    html = template
    
    # Injetar variáveis de contexto da página primeiro
    html = html.replace("@local", page['location'])
    html = html.replace("@keyword", page['keyword'])
    
    replaced_count = 0
    for key, value in flat_result.items():
        # Normalizar key: lowercase, sem espaços
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

    # Salvar
    output_path = os.path.join(output_dir, page['filename'])
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)



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


def _replace_config_vars(template: str, config: dict) -> str:
    """Substitui variáveis de configuração ({{var}}) no template."""
    empresa = config['empresa']
    r, g, b = hex_to_rgb(empresa['cor_marca'])

    replacements = {
        '{{empresa_nome}}': empresa['nome'],
        '{{empresa_categoria}}': empresa['categoria'],
        '{{telefone_whatsapp}}': empresa['telefone_whatsapp'],
        '{{telefone_display}}': get_phone_display(config),
        '{{whatsapp_link}}': get_whatsapp_link(config),
        '{{cor_marca}}': empresa['cor_marca'],
        '{{cor_marca_rgb}}': f"{r}, {g}, {b}",
        '{{google_maps_url}}': empresa.get('google_maps_embed', ''),
        '{{dominio}}': empresa['dominio'],
        '{{horario}}': empresa.get('horario', ''),
        '{{ano}}': str(__import__('datetime').datetime.now().year),
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    return template


def _log_error(page_title: str, error: str, output_dir: str):
    """Registra erros em arquivo de log."""
    log_path = os.path.join(output_dir, '..', 'error_log.txt')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n--- ERROR: {page_title} ---\n{error}\n")
