"""
Autoridade Sites - Orquestrador Principal (CLI)

Uso:
    python generate.py                   # Executa todo o pipeline
    python generate.py --step mix        # Só gera o mix
    python generate.py --step sitemap    # Só gera o sitemap
    python generate.py --step topics     # Só gera tópicos
    python generate.py --step home       # Só gera a home page (SiteGen)
    python generate.py --step pages      # Só gera as subpáginas SEO
    python generate.py --step validate   # Só valida
    python generate.py --config outro.yaml  # Usa outro arquivo de config
"""
import sys
import time
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

from core.config_loader import load_config, get_whatsapp_link, get_phone_display
from core.mixer import mix_keywords_locations, get_summary
from core.sitemap_generator import generate_sitemap
from core.openrouter_client import OpenRouterClient
from core.topic_generator import generate_topics
from core.page_generator import generate_all_pages, get_retry_log, _replace_config_vars
from core.validator import validate_site, generate_report
from core.site_data_builder import build_site_data, resolve_theme_mode
from core.template_injector import inject_template
from core.imagen_client import GeminiImageClient
from core.output_builder import setup_output_dir, generate_fallback_index


def main():
    parser = argparse.ArgumentParser(description="Autoridade Sites - Gerador de Sites SEO com IA")
    parser.add_argument('--config', default='config.yaml', help='Arquivo de configuração')
    parser.add_argument('--step', choices=['mix', 'sitemap', 'topics', 'image', 'home', 'pages', 'validate', 'all'],
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
        setup_output_dir(output_dir, config)

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

    # 6.5 Resolver tema (leve — ~3s) — necessário para imagem, home e subpáginas
    if args.step in ('all', 'home', 'pages', 'image'):
        resolve_theme_mode(config, client)
        print()

    # 6.6 Gerar Imagem Hero (Imagen 3) — usa theme_mode já resolvido
    theme_mode = config.get('theme', {}).get('mode', 'dark')
    hero_img_path = Path(output_dir) / "hero-image.jpg"
    if args.step in ('all', 'home', 'image'):
        # Também gerar em images/hero.jpg para subpáginas HTML puras
        hero_img_legacy = Path(output_dir) / "images" / "hero.jpg"
        if not hero_img_path.exists() and not hero_img_legacy.exists():
            print("🎨 Gerando Imagem Hero com Google Gemini...")
            try:
                img_client = GeminiImageClient()
                img_client.generate_hero(
                    categoria=config['empresa']['categoria'],
                    nome=config['empresa']['nome'],
                    output_path=str(hero_img_path),
                    keywords=config.get('seo', {}).get('palavras_chave', []),
                    theme_mode=theme_mode
                )
                # Copiar para caminho legado (subpáginas HTML puras)
                hero_img_legacy.parent.mkdir(parents=True, exist_ok=True)
                if hero_img_path.exists():
                    shutil.copy2(str(hero_img_path), str(hero_img_legacy))
            except Exception as e:
                print(f"  ⚠ Aviso: Não foi possível gerar imagem hero: {e}")
        else:
            print("🎨 Imagem Hero já existe. Pulando geração.")
        print()

    # 6.7 Gerar Home Page (SiteGen Template)
    if args.step in ('all', 'home'):
        print("🏠 Gerando conteúdo da home page via IA...")
        try:
            site_data = build_site_data(config, client)
            print()
            print("🏠 Injetando home page premium (SiteGen)...")
            inject_template(
                site_data=site_data,
                output_dir=output_dir,
                hero_image_path=str(hero_img_path) if hero_img_path.exists() else None,
            )
        except Exception as e:
            print(f"  ⚠ Erro na home SiteGen: {e}")
            print("  ↳ Gerando home com template HTML fallback...")
            generate_fallback_index(config, output_dir)
        print()

    if args.step == 'home':
        _print_done(start_time)
        return

    # 7. Gerar páginas SEO
    if args.step in ('all', 'pages'):
        print("⚡ Gerando páginas SEO...")
        template_path = Path("templates") / "page.html"
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
        report = generate_report(results, config, api_stats, output_dir, retry_log=get_retry_log())

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





def _print_done(start_time: float):
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"✅ Concluído em {minutes}m {seconds}s")


if __name__ == "__main__":
    main()
