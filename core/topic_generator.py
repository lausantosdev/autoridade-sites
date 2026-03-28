"""
Topic Generator - Gera tópicos/frases específicos do nicho via IA
"""
import os
import json
import random
from core.openrouter_client import OpenRouterClient


CACHE_DIR = "cache"


def generate_topics(config: dict, client: OpenRouterClient, force: bool = False) -> dict:
    """
    Gera tópicos e frases específicos para o nicho configurado.
    Cacheia o resultado para reutilização.
    
    Returns:
        Dict com 'palavras' (list) e 'frases' (list)
    """
    categoria = config['empresa']['categoria']
    cache_path = os.path.join(CACHE_DIR, f"topicos_{_safe_filename(categoria)}.json")

    # Retorna cache se existir (e não forçar regeneração)
    if not force and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print(f"  ✓ Tópicos carregados do cache ({len(cached['palavras'])} palavras, {len(cached['frases'])} frases)")
        return cached

    print(f"  ⏳ Gerando tópicos para o nicho: {categoria}...")

    system_prompt = "Você é um especialista em SEO e marketing de conteúdo. Responda apenas em JSON."

    user_prompt = f"""Gere conteúdo para SEO no nicho de "{categoria}".

Retorne um JSON com duas listas:

1. "palavras": 100 palavras-chave técnicas e termos relevantes do nicho "{categoria}".
   Devem ser termos que um profissional da área usaria. Uma palavra ou termo curto por item.

2. "frases": 100 frases descritivas sobre temas do nicho "{categoria}".
   Cada frase deve ser um mini-tópico que pode virar um título H2 ou tema de parágrafo.
   As frases devem ser variadas, cobrindo diferentes aspectos do nicho.

Formato esperado:
{{
    "palavras": ["palavra1", "palavra2", ...],
    "frases": ["frase descritiva 1", "frase descritiva 2", ...]
}}"""

    result = client.generate_json(system_prompt, user_prompt)

    if not result or 'palavras' not in result or 'frases' not in result:
        print("  ⚠ Falha ao gerar tópicos. Usando tópicos genéricos.")
        result = _fallback_topics(categoria)

    # Cachear resultado
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Tópicos gerados: {len(result['palavras'])} palavras, {len(result['frases'])} frases")
    return result


def get_random_mix(topics: dict, count: int = 6) -> list:
    """Gera mixes aleatórios de palavras + frases para variação de prompt."""
    mixes = []
    palavras = topics.get('palavras', [])
    frases = topics.get('frases', [])

    for _ in range(count):
        parts = []
        if palavras:
            parts.append(random.choice(palavras))
        if frases:
            parts.append(random.choice(frases))
        mixes.append(' '.join(parts))

    return mixes


def _safe_filename(text: str) -> str:
    """Converte texto para nome de arquivo seguro."""
    import re
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def _fallback_topics(categoria: str) -> dict:
    """Tópicos genéricos de fallback caso a API falhe."""
    return {
        "palavras": [
            "qualidade", "profissional", "especialista", "confiança",
            "resultado", "atendimento", "experiência", "garantia",
            "solução", "eficiência", "inovação", "tecnologia",
            "compromisso", "excelência", "tradição", "modernidade"
        ],
        "frases": [
            f"Como escolher o melhor serviço de {categoria}",
            f"Benefícios de contratar um especialista em {categoria}",
            f"Dicas importantes sobre {categoria} para iniciantes",
            f"Por que investir em {categoria} de qualidade",
            f"Tendências atuais no mercado de {categoria}",
            f"Erros comuns ao contratar serviços de {categoria}",
        ]
    }

def generate_services_data(config: dict, client: OpenRouterClient) -> list:
    """Gera descrições genéricas + ícones para os serviços inseridos manualmente."""
    servicos = config['empresa'].get('servicos_manuais', [])
    if not servicos:
        return []

    system_prompt = "Você é um especialista em Copywriting. Responda APENAS com um Array JSON."
    servicos_str = "\\n".join(f"- {s}" for s in servicos)

    user_prompt = f"""Crie uma breve descrição comercial e persuasiva (máx 22 palavras) para cada um dos serviços listados abaixo.
Escolha também uma classe de ícone FontAwesome 6 (mantenha o prefixo fas fa-) que represente o serviço adequadamente.

Lista de Serviços Reais:
{servicos_str}

Retorne ESTRITAMENTE um JSON válido contendo um array de objetos, assim:
[
  {{"titulo": "Nome igual da lista", "descricao": "Descrição gerada...", "icone": "fas fa-bolt"}}
]"""

    result = client.generate_json(system_prompt, user_prompt)
    if isinstance(result, list):
        return result
    elif isinstance(result, dict) and "servicos" in result:
        return result["servicos"]
    return []
