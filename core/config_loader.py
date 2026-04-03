"""
Config Loader - Carrega e valida config.yaml + CSV de keywords
"""
import os
import csv
import yaml
from pathlib import Path
import urllib.parse


def load_config(config_path: str = "config.yaml") -> dict:
    """Carrega o arquivo config.yaml e valida os campos obrigatórios."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Validação dos campos obrigatórios
    required_empresa = ['nome', 'dominio', 'categoria', 'telefone_whatsapp']
    for field in required_empresa:
        if not config.get('empresa', {}).get(field):
            raise ValueError(f"Campo obrigatório ausente: empresa.{field}")

    # Carregar palavras-chave (do CSV ou da lista manual)
    config['seo']['palavras_chave'] = _load_keywords(config.get('seo', {}))

    # Validar que temos palavras-chave e locais
    if not config['seo'].get('palavras_chave'):
        raise ValueError("Nenhuma palavra-chave encontrada. Adicione em seo.palavras_chave ou seo.palavras_chave_csv")
    if not config['seo'].get('locais'):
        raise ValueError("Nenhum local encontrado. Adicione em seo.locais")

    # Defaults para campos opcionais
    config.setdefault('api', {})
    config['api'].setdefault('provider', 'openrouter')
    config['api'].setdefault('model', 'deepseek/deepseek-v3.2')
    config['api'].setdefault('max_workers', 30)
    config['api'].setdefault('max_retries', 3)

    config.setdefault('leads', {})
    config['leads'].setdefault('worker_url', '')
    config['leads'].setdefault('client_token', '')

    config.setdefault('template', {})
    config['template'].setdefault('preset', 'custom')

    config['empresa'].setdefault('cor_marca', '#2563EB')
    config['empresa'].setdefault('horario', 'Segunda a Sexta, 8h às 18h')
    config['empresa'].setdefault('telefone_ligar', config['empresa']['telefone_whatsapp'])
    config['empresa'].setdefault('google_maps_embed', '')

    return config


def _load_keywords(seo_config: dict) -> list:
    """Carrega palavras-chave do CSV do Google Keyword Planner ou da lista manual."""
    keywords = []

    # Tenta carregar do CSV primeiro
    csv_path = seo_config.get('palavras_chave_csv')
    if csv_path and os.path.exists(csv_path):
        keywords = _parse_keyword_csv(csv_path)
        print(f"  ✓ {len(keywords)} palavras-chave importadas do CSV: {csv_path}")

    # Se não tem CSV, usa a lista manual
    if not keywords:
        keywords = seo_config.get('palavras_chave', [])

    # Capitaliza todas
    keywords = [kw.strip().title() for kw in keywords if kw.strip()]

    return keywords


def _parse_keyword_csv(csv_path: str) -> list:
    """
    Faz parsing do CSV exportado pelo Google Keyword Planner.
    Tenta UTF-8 primeiro, depois Latin-1 (comum em exports do Windows BR).
    """
    for encoding in ('utf-8-sig', 'latin-1'):
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                return _parse_csv_content(f)
        except UnicodeDecodeError:
            continue
    return []


def _parse_csv_content(f) -> list:
    """Parse do conteúdo CSV já aberto."""
    keywords = []
    # Tenta detectar se é CSV com headers
    sample = f.read(2048)
    f.seek(0)

    if ',' in sample.split('\n')[0]:
        reader = csv.DictReader(f)
        headers = [h.lower().strip() for h in (reader.fieldnames or [])]

        keyword_col = None
        for h in headers:
            if h in ('keyword', 'keywords', 'palavra-chave', 'palavra chave', 'term'):
                keyword_col = h
                break

        if keyword_col is None and headers:
            keyword_col = headers[0]

        volume_col = None
        for h in headers:
            if any(v in h for v in ('volume', 'searches', 'search vol', 'avg.')):
                volume_col = h
                break

        for row in reader:
            kw = row.get(keyword_col, '').strip()
            if kw and not kw.startswith('#'):
                keywords.append(kw)
    else:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                keywords.append(line)

    return keywords


def get_whatsapp_link(config: dict, message: str = "Olá, gostaria de mais informações.") -> str:
    """Gera link do WhatsApp com mensagem pré-formatada."""
    phone = config['empresa']['telefone_whatsapp']
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_msg}"


def get_phone_display(config: dict) -> str:
    """Formata número de telefone para exibição."""
    phone = config['empresa'].get('telefone_ligar', config['empresa']['telefone_whatsapp'])
    # Remove prefixo do país se presente
    if phone.startswith('55') and len(phone) >= 12:
        phone = phone[2:]
    if len(phone) == 11:
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    return phone
