"""
Validator - Valida qualidade das páginas geradas
"""
import os
import re
from datetime import datetime
from core.logger import get_logger
logger = get_logger(__name__)


# Campos obrigatórios que a IA deve retornar no JSON.
# Se algum desses virar placeholder no HTML (@campo), a página é inválida.
CRITICAL_FIELDS = [
    'titulo', 'meta_description',
    'hero_titulo_linha_1', 'hero_titulo_destaque', 'hero_titulo_linha_3', 'hero_subtitulo',
    'diferencial_1_titulo', 'diferencial_2_titulo', 'diferencial_3_titulo',
    'autoridade_titulo', 'autoridade_manifesto',
    'cta_titulo', 'cta_subtitulo',
    'faq_1_pergunta', 'faq_1_resposta',
    'seo_h2_1', 'seo_p1', 'seo_h2_2', 'seo_p2',
    'seo_h2_3', 'seo_p3', 'seo_h2_4', 'seo_p4',
    'seo_h2_5', 'seo_p5', 'seo_h2_6', 'seo_p6',
]

# At-rules CSS legítimas — NÃO são placeholders
CSS_AT_RULES = {'media', 'keyframes', 'font-face', 'import', 'charset', 'supports', 'layer'}


def validate_page_html(filename: str, html: str) -> dict:
    """
    Validação rápida em memória para uso DURANTE a geração (antes de salvar).
    
    Retorna:
        {
            'valid': bool,        # True = pode salvar, False = precisa retry
            'errors': [str],      # Motivos de bloqueio
            'warnings': [str],    # Apenas informativos
            'word_count': int
        }
    """
    result = {'valid': True, 'errors': [], 'warnings':[], 'word_count': 0}

    # --- ERROS (bloqueantes — forçam retry) ---

    # 1. Título ausente
    title_match = re.search(r'<title>(.*?)</title>', html)
    if not title_match or not title_match.group(1).strip():
        result['errors'].append(f"{filename}: Título <title> ausente ou vazio")

    # 2. Placeholders @campo não substituídos (excluindo scripts e at-rules CSS)
    html_no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    raw_placeholders = re.findall(r'@([a-z_][a-z_0-9]*)', html_no_scripts)
    bad_placeholders = [
        f"@{p}" for p in raw_placeholders
        if p not in CSS_AT_RULES
        and p not in ('whatsapp_pagina',)  # Já substituído antes da validação
    ]
    if bad_placeholders:
        unique = list(dict.fromkeys(bad_placeholders))  # Remove duplicatas mantendo ordem
        result['errors'].append(
            f"{filename}: {len(unique)} placeholders não substituídos: {unique[:8]}"
        )

    # 3. Config vars {{var}} não substituídas
    config_vars = re.findall(r'\{\{[a-z_]+\}\}', html_no_scripts)
    if config_vars:
        result['errors'].append(
            f"{filename}: Config vars não substituídas: {config_vars[:5]}"
        )

    # 4. Contagem de palavras — < 500 = página truncada/vazia (bloqueante)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    word_count = len(text.split())
    result['word_count'] = word_count

    if word_count < 500:
        result['errors'].append(
            f"{filename}: Apenas {word_count} palavras (mínimo bloqueante: 500)"
        )

    # --- WARNINGS (apenas reportados, não bloqueiam) ---

    if word_count < 900:
        result['warnings'].append(f"{filename}: Apenas {word_count} palavras (ideal: 900+)")

    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    if len(h2s) < 6:
        result['warnings'].append(f"{filename}: Apenas {len(h2s)} H2s (ideal: 6)")

    internal_links = re.findall(r'href="([^"]*\.html)"', html)
    if len(internal_links) < 2:
        result['warnings'].append(f"{filename}: Apenas {len(internal_links)} links internos")

    # --- Resultado final ---
    if result['errors']:
        result['valid'] = False

    return result


def validate_site(output_dir: str, config: dict) -> dict:
    """
    Valida todas as páginas HTML geradas.
    
    Returns:
        Dict com estatísticas e lista de problemas.
    """
    results = {
        'total_pages': 0,
        'valid_pages': 0,
        'warnings': [],
        'errors': [],
        'stats': {}
    }

    html_files = [f for f in os.listdir(output_dir) if f.endswith('.html')]
    results['total_pages'] = len(html_files)

    total_words = 0

    for filename in html_files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        page_issues = _validate_page(filename, content, config)

        if page_issues['errors']:
            results['errors'].extend(page_issues['errors'])
        elif page_issues['warnings']:
            results['warnings'].extend(page_issues['warnings'])
            results['valid_pages'] += 1
        else:
            results['valid_pages'] += 1

        total_words += page_issues.get('word_count', 0)

    results['stats'] = {
        'total_words': total_words,
        'avg_words_per_page': total_words // max(len(html_files), 1),
        'total_size_kb': sum(
            os.path.getsize(os.path.join(output_dir, f))
            for f in html_files
        ) // 1024
    }

    return results


def _validate_page(filename: str, content: str, config: dict = None) -> dict:
    """Valida uma única página."""
    issues = {'errors': [], 'warnings': [], 'word_count': 0}

    # Verificar título
    title_match = re.search(r'<title>(.*?)</title>', content)
    if not title_match or not title_match.group(1).strip():
        issues['errors'].append(f"{filename}: Título ausente ou vazio")
    elif '@' in title_match.group(1):
        issues['errors'].append(f"{filename}: Placeholder não substituído no título")

    # Verificar meta description
    desc_match = re.search(r'<meta name="description" content="(.*?)"', content)
    if not desc_match or not desc_match.group(1).strip():
        issues['warnings'].append(f"{filename}: Meta description ausente")
    elif '@' in desc_match.group(1):
        issues['errors'].append(f"{filename}: Placeholder não substituído na meta description")

    # Verificar H1
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    if not h1_match:
        issues['warnings'].append(f"{filename}: H1 ausente")

    # Verificar H2s
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL)
    if len(h2s) < 6:
        issues['warnings'].append(f"{filename}: Apenas {len(h2s)} H2s (mínimo recomendado: 6)")

    # Verificar placeholders não substituídos (ignorar blocos <script> para não confundir com JSON-LD)
    content_no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    CSS_AT_RULES = {'media', 'keyframes', 'font-face', 'import', 'charset', 'supports', 'layer'}
    placeholders = [
        p for p in re.findall(r'@[a-z_]+', content_no_scripts)
        if p[1:] not in CSS_AT_RULES
    ]
    if placeholders:
        issues['errors'].append(
            f"{filename}: {len(placeholders)} placeholders não substituídos: {placeholders[:5]}"
        )

    config_placeholders = re.findall(r'\{\{[a-z_]+\}\}', content_no_scripts)
    if config_placeholders:
        issues['errors'].append(
            f"{filename}: Config vars não substituídas: {config_placeholders[:5]}"
        )

    # Contar palavras do conteúdo SEO
    text = re.sub(r'<[^>]+>', ' ', content)
    text = re.sub(r'\s+', ' ', text).strip()
    word_count = len(text.split())
    issues['word_count'] = word_count

    if word_count < 900:
        issues['warnings'].append(f"{filename}: Apenas {word_count} palavras (mínimo: 900)")

    # Verificar links internos
    internal_links = re.findall(r'href="([^"]*\.html)"', content)
    if len(internal_links) < 2 and filename != 'index.html' and filename != 'mapa-do-site.html':
        issues['warnings'].append(f"{filename}: Apenas {len(internal_links)} links internos")

    return issues


def generate_report(results: dict, config: dict, api_stats: dict, output_dir: str, retry_log: list = None) -> str:
    """Gera relatório de qualidade em Markdown."""
    empresa = config['empresa']['nome']
    now = datetime.now().strftime('%d/%m/%Y %H:%M')

    report = f"""# 📊 Relatório de Geração - {empresa}
**Data:** {now}

## Resumo
| Métrica | Valor |
|---|---|
| Total de páginas | {results['total_pages']} |
| Páginas válidas | {results['valid_pages']} |
| Erros | {len(results['errors'])} |
| Avisos | {len(results['warnings'])} |
| Total de palavras | {results['stats'].get('total_words', 0):,} |
| Média palavras/página | {results['stats'].get('avg_words_per_page', 0):,} |
| Tamanho total | {results['stats'].get('total_size_kb', 0):,} KB |

## Custos da API
| Métrica | Valor |
|---|---|
| Chamadas à API | {api_stats['calls']} |
| Tokens de entrada | {api_stats['input_tokens']:,} |
| Tokens de saída | {api_stats['output_tokens']:,} |
| Custo total (USD) | ${api_stats['cost_usd']:.4f} |
| Custo total (BRL) | R${api_stats['cost_brl']:.2f} |
"""

    if results['errors']:
        report += "\n## ❌ Erros\n"
        for err in results['errors']:
            report += f"- {err}\n"

    if results['warnings']:
        report += "\n## ⚠️ Avisos\n"
        for warn in results['warnings'][:20]:  # Limitar a 20
            report += f"- {warn}\n"
        if len(results['warnings']) > 20:
            report += f"\n... e mais {len(results['warnings']) - 20} avisos\n"

    if retry_log:
        report += "\n## 🔄 Retries\n"
        # Agrupar por página
        pages_retried = {}
        for entry in retry_log:
            page = entry['page']
            if page not in pages_retried:
                pages_retried[page] = {'max_attempt': 0, 'errors': []}
            pages_retried[page]['max_attempt'] = max(
                pages_retried[page]['max_attempt'], entry['attempt']
            )
            pages_retried[page]['errors'] = entry['errors']

        max_retries_config = config.get('api', {}).get('max_retries', 3)
        recovered = 0
        failed = 0
        for page, info in pages_retried.items():
            if info['max_attempt'] < max_retries_config:
                status = "✅"
                recovered += 1
            else:
                status = "❌"
                failed += 1
            report += f"- {page}: {status} {info['max_attempt']} tentativa(s) — {info['errors'][0] if info['errors'] else 'erro desconhecido'}\n"

        report += f"\n| Páginas com retry | {len(pages_retried)} |\n"
        report += f"| Recuperadas | {recovered} |\n"
        report += f"| Perdidas | {failed} |\n"

    report += f"\n---\n*Gerado por Autoridade Sites SEO Generator*\n"

    # Salvar relatório
    reports_dir = os.path.join(output_dir, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, f"{config['empresa']['dominio']}_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info("Relatório salvo em: %s", report_path)
    return report
