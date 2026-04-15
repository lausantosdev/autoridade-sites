"""
SiteGen - Orquestrador Principal (CLI)

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
from core.gemini_client import GeminiClient
from core.topic_generator import generate_topics
from core.page_generator import generate_all_pages, get_retry_log, _replace_config_vars
from core.validator import validate_site, generate_report
from core.site_data_builder import build_site_data, resolve_theme_mode
from core.template_injector import inject_template
from core.imagen_client import GeminiImageClient
from core.output_builder import setup_output_dir, generate_fallback_index, build_static_home_page


def main():
    parser = argparse.ArgumentParser(description="SiteGen - Gerador de Sites SEO com IA")
    parser.add_argument('--config', default='config.yaml', help='Arquivo de configuração')
    parser.add_argument('--step', choices=['mix', 'sitemap', 'topics', 'image', 'home', 'pages', 'validate', 'all'],
                        default='all', help='Passo específico a executar')
    parser.add_argument('--force-topics', action='store_true', help='Forçar regeneração de tópicos')
    parser.add_argument('--static-test', action='store_true',
                        help='Usa o pipeline estático (index_static.html) ao invés do SiteGen React. '
                             'Apenas para testes locais — não afeta produção.')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🚀 SITEGEN - Gerador de Sites SEO com IA")
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



    try:
        client = OpenRouterClient(
            model=config['api']['model'],
            max_retries=config['api']['max_retries']
        )
    except Exception as e:
        from core.gemini_client import GeminiClient
        print(f"  [!] OpenRouter indisponível ({e}). Usando GeminiClient...")
        client = GeminiClient(model='gemini-2.5-flash')

    # GeminiClient como primário (structured output, mais rápido)
    gemini = None
    try:
        gemini = GeminiClient(model='gemini-2.5-flash')
        print("🚀 GeminiClient ativo — usando como primário (OpenRouter = fallback)")
    except Exception as e:
        print(f"⚠️ GeminiClient indisponível ({e}) — usando apenas OpenRouter")

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

    theme_mode = config.get('theme', {}).get('mode', 'dark')
    hero_img_path = Path(output_dir) / "hero-image.webp"

    # ── Fase paralela (--step all): Hero + Home Data ──────────────
    # Topics já foi executado acima (pode usar cache).
    # Hero e Home Data são independentes e podem rodar em paralelo.
    if args.step == 'all':
        from concurrent.futures import ThreadPoolExecutor, as_completed

        need_hero = not hero_img_path.exists()

        def _run_hero():
            if not need_hero:
                return
            img_client = GeminiImageClient()
            img_client.generate_hero(
                categoria=config['empresa']['categoria'],
                nome=config['empresa']['nome'],
                output_path=str(hero_img_path),
                keywords=config.get('seo', {}).get('palavras_chave', []),
                theme_mode=theme_mode,
                llm_client=client,
            )

        def _run_home_data():
            return build_site_data(config, client)

        print("⚡ Gerando imagem hero + home page em paralelo...")
        site_data = None
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_hero = executor.submit(_run_hero)
            future_home = executor.submit(_run_home_data)

            try:
                site_data = future_home.result()
            except Exception as e:
                print(f"  ⚠ Erro na home SiteGen: {e}")

            try:
                future_hero.result()
                if need_hero:
                    print("  ✓ Imagem hero gerada")
                else:
                    print("  ✓ Imagem hero já existia")
            except Exception as e:
                print(f"  ⚠ Aviso: Não foi possível gerar imagem hero: {e}")

        # Injetar home page (precisa de site_data + hero_img_path prontos)
        if site_data:
            print("🏠 Injetando home page premium (SiteGen)...")
            try:
                # Usar a versão correta dependendo de args.static_test
                if getattr(args, 'static_test', False):
                    build_static_home_page(config, site_data, output_dir)
                else:
                    inject_template(
                        site_data=site_data,
                        output_dir=output_dir,
                        hero_image_path=str(hero_img_path) if hero_img_path.exists() else None,
                    )
            except Exception as e:
                print(f"  ⚠ Erro ao injetar home: {e}")
                print("  ↳ Gerando home com template HTML fallback...")
                generate_fallback_index(config, output_dir)
        else:
            print("  ↳ Gerando home com template HTML fallback...")
            generate_fallback_index(config, output_dir)
        print()

    else:
        # Modo individual: manter sequencial para debug
        # 6.6 Gerar Imagem Hero (Imagen 3)
        if args.step in ('home', 'image'):
            if not hero_img_path.exists():
                print("🎨 Gerando Imagem Hero com Google Gemini...")
                try:
                    img_client = GeminiImageClient()
                    img_client.generate_hero(
                        categoria=config['empresa']['categoria'],
                        nome=config['empresa']['nome'],
                        output_path=str(hero_img_path),
                        keywords=config.get('seo', {}).get('palavras_chave', []),
                        theme_mode=theme_mode,
                        llm_client=client,
                    )
                except Exception as e:
                    print(f"  ⚠ Aviso: Não foi possível gerar imagem hero: {e}")
            else:
                print("🎨 Imagem Hero já existe. Pulando geração.")
            print()

        # 6.7 Gerar Home Page (SiteGen Template ou Estático)
        if args.step == 'home':
            if args.static_test:
                # ── Pipeline Estático (index_static.html — Premium com IA) ──
                print("🏠 Gerando dados da home page via IA...")
                try:
                    site_data = build_site_data(config, client)
                    print()
                    print("🏠 Gerando home ESTÁTICA PREMIUM...")
                    result_path = build_static_home_page(config, site_data, output_dir)
                    print(f"  ✓ Home estática gerada: {result_path}")
                except Exception as e:
                    print(f"  ⚠ Erro na home estática (IA): {e}")
                    print("  ↳ Usando fallback padrão...")
                    generate_fallback_index(config, output_dir)
            else:
                # ── Pipeline React original (intacto) ──
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
            output_dir=output_dir,
            gemini_client=gemini
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
