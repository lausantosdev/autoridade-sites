"""
Autoridade Sites - Orquestrador Principal (CLI)

Uso:
    python generate.py                   # Executa todo o pipeline
    python generate.py --step mix        # Só gera o mix
    python generate.py --step sitemap    # Só gera o sitemap
    python generate.py --step topics     # Só gera tópicos
    python generate.py --step pages      # Só gera as páginas
    python generate.py --step validate   # Só valida
    python generate.py --config outro.yaml  # Usa outro arquivo de config
"""
import sys
import time
import shutil
import argparse
from pathlib import Path

from core.config_loader import load_config
from core.mixer import mix_keywords_locations, get_summary
from core.sitemap_generator import generate_sitemap
from core.openrouter_client import OpenRouterClient
from core.topic_generator import generate_topics
from core.page_generator import generate_all_pages
from core.validator import validate_site, generate_report


TEMPLATES_DIR = Path("templates")


def main():
    parser = argparse.ArgumentParser(description="Autoridade Sites - Gerador de Sites SEO com IA")
    parser.add_argument('--config', default='config.yaml', help='Arquivo de configuração')
    parser.add_argument('--step', choices=['mix', 'sitemap', 'topics', 'pages', 'validate', 'all'],
                        default='all', help='Passo específico a executar')
    parser.add_argument('--force-topics', action='store_true', help='Forçar regeneração de tópicos')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🚀 AUTORIDADE SITES - Gerador de Sites SEO com IA")
    print("=" * 60 + "\n")

    start_time = time.time()

    # 1. Carregar configuração
    print("📋 Carregando configuração...")
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        sys.exit(1)

    empresa = config['empresa']['nome']
    dominio = config['empresa']['dominio']
    output_dir = str(Path("output") / dominio)

    print(f"  ✓ Empresa: {empresa}")
    print(f"  ✓ Domínio: {dominio}")
    print(f"  ✓ Palavras-chave: {len(config['seo']['palavras_chave'])}")
    print(f"  ✓ Locais: {len(config['seo']['locais'])}")
    print(f"  ✓ API: {config['api']['model']}")
    print()

    # 2. Gerar mix de palavras × locais
    if args.step in ('all', 'mix'):
        print("🔀 Gerando mix de palavras-chave × locais...")
        pages = mix_keywords_locations(
            config['seo']['palavras_chave'],
            config['seo']['locais']
        )
        print(f"  ✓ {get_summary(pages)}")
        print()
    else:
        pages = mix_keywords_locations(
            config['seo']['palavras_chave'],
            config['seo']['locais']
        )

    if args.step == 'mix':
        _print_done(start_time)
        return

    # 3. Copiar assets do template para output
    if args.step in ('all', 'sitemap', 'pages'):
        _setup_output_dir(output_dir, config)

    # 4. Gerar sitemap
    if args.step in ('all', 'sitemap'):
        print("🗺️  Gerando sitemap...")
        generate_sitemap(pages, config, output_dir)
        print()

    if args.step == 'sitemap':
        _print_done(start_time)
        return

    # 5. Inicializar client API
    client = OpenRouterClient(
        model=config['api']['model'],
        max_retries=config['api']['max_retries']
    )

    # 6. Gerar tópicos do nicho
    if args.step in ('all', 'topics'):
        print("📝 Gerando tópicos do nicho...")
        topics = generate_topics(config, client, force=args.force_topics)
        print()
    else:
        topics = generate_topics(config, client)

    if args.step == 'topics':
        _print_done(start_time)
        return

    # 7. Gerar páginas SEO
    if args.step in ('all', 'pages'):
        print("⚡ Gerando páginas SEO...")
        template_path = TEMPLATES_DIR / "page.html"
        if not template_path.exists():
            print(f"  ❌ Template não encontrado: {template_path}")
            sys.exit(1)

        generate_all_pages(
            pages=pages,
            config=config,
            topics=topics,
            client=client,
            template_path=str(template_path),
            output_dir=output_dir
        )
        print()

    # 8. Validar
    if args.step in ('all', 'validate'):
        print("🔍 Validando qualidade...")
        results = validate_site(output_dir, config)
        api_stats = client.get_stats()
        report = generate_report(results, config, api_stats, output_dir)

        print(f"  ✓ {results['valid_pages']}/{results['total_pages']} páginas válidas")
        if results['errors']:
            print(f"  ⚠ {len(results['errors'])} erros encontrados (ver relatório)")
        print()

    _print_done(start_time)

    # Mostrar custos
    stats = client.get_stats()
    if stats['calls'] > 0:
        print(f"\n💰 Custo total: ${stats['cost_usd']:.4f} USD (~R${stats['cost_brl']:.2f})")
        print(f"   Tokens: {stats['total_tokens']:,} ({stats['input_tokens']:,} in / {stats['output_tokens']:,} out)")


def _setup_output_dir(output_dir: str, config: dict):
    """Copia assets estáticos do template para o diretório de saída."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copiar CSS
    css_src = TEMPLATES_DIR / "css"
    css_dst = output_path / "css"
    if css_src.exists() and not css_dst.exists():
        shutil.copytree(str(css_src), str(css_dst))
        
    # Processar variáveis no arquivo CSS copiado sempre
    css_path = css_dst / "style.css"
    if css_path.exists():
        from core.page_generator import _replace_config_vars
        css_content = css_path.read_text(encoding='utf-8')
        css_content = _replace_config_vars(css_content, config)
        css_path.write_text(css_content, encoding='utf-8')

    # Copiar JS
    js_src = TEMPLATES_DIR / "js"
    js_dst = output_path / "js"
    if js_src.exists() and not js_dst.exists():
        shutil.copytree(str(js_src), str(js_dst))

    # Criar js/dados.js dinamicamente com base nas configurações
    import json
    from core.config_loader import get_whatsapp_link, get_phone_display

    dados_js = {
        "empresa_nome": config['empresa']['nome'],
        "empresa_categoria": config['empresa']['categoria'],
        "telefone_whatsapp": config['empresa']['telefone_whatsapp'],
        "telefone_link": f"tel:{config['empresa']['telefone_whatsapp']}",
        "telefone_display": get_phone_display(config),
        "whatsapp_link": get_whatsapp_link(config),
        "horario": config['empresa'].get('horario', ''),
        "google_maps_url": config['empresa'].get('google_maps_embed', ''),
        "dominio": config['empresa']['dominio'],
        "ano": str(__import__('datetime').datetime.now().year)
    }

    # Assegurar que pasta JS existe
    js_dst.mkdir(parents=True, exist_ok=True)
    dados_path = js_dst / "dados.js"
    
    # Criar conteúdo do script
    script_content = f"// Criado automaticamente - Autoridade Sites\n"
    script_content += f"const DadosSite = {json.dumps(dados_js, indent=4, ensure_ascii=False)};\n"
    
    with open(dados_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    # Copiar images (se existirem)
    img_src = TEMPLATES_DIR / "images"
    img_dst = output_path / "images"
    if img_src.exists() and not img_dst.exists():
        shutil.copytree(str(img_src), str(img_dst))

    # Import module level function and call it to generate index.html
    _generate_index(config, output_dir)


def _generate_index(config: dict, output_dir: str):
    """Gera a index.html a partir do template."""
    from core.page_generator import _replace_config_vars
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        content = index_template.read_text(encoding='utf-8')
        content = _replace_config_vars(content, config)
        output_path = Path(output_dir) / "index.html"
        output_path.write_text(content, encoding='utf-8')


def _print_done(start_time: float):
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"✅ Concluído em {minutes}m {seconds}s")


if __name__ == "__main__":
    main()
