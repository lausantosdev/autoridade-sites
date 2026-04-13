"""
Job Queue para geração assíncrona de sites.
Estado sempre persistido no Supabase antes de cada step.
"""
import os
import re
import asyncio
import traceback
from datetime import datetime, timezone
from uuid import UUID

from core.supabase_client import get_supabase
import logging

logger = logging.getLogger(__name__)


def _extract_maps_url(value: str) -> str:
    """Extrai a URL de embed do Google Maps.

    Aceita tanto a URL direta quanto um iframe HTML completo cole do Google Maps.
    Se for um iframe, extrai o valor do atributo src.
    """
    if not value:
        return ''
    value = value.strip()
    if '<iframe' in value:
        match = re.search(r'src=["\']([^"\']+)["\']', value)
        if match:
            return match.group(1)
        return ''
    return value

async def _append_log(job_id: str, level: str, message: str) -> None:
    """Adiciona uma entrada de log ao job no Supabase."""
    sb = get_supabase()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,   # "info" | "warning" | "error"
        "message": message,
    }
    # Usar função RPC para append atômico ao jsonb sem race condition
    sb.rpc("append_job_log", {"job_id": job_id, "log_entry": entry}).execute()


async def update_job_step(
    job_id: str,
    step: str,
    progress_pct: int,
    status: str = "generating",
) -> None:
    """
    Atualiza step, progresso e status do job.
    DEVE ser chamado antes de qualquer operação pesada.
    """
    sb = get_supabase()
    payload = {
        "status": status,
        "step": step,
        "progress_pct": progress_pct,
    }
    if status == "generating" and step == "queue":
        payload["started_at"] = datetime.now(timezone.utc).isoformat()
    if status in ("complete", "failed"):
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()

    sb.table("jobs").update(payload).eq("id", job_id).execute()
    await _append_log(job_id, "info", f"Step: {step} ({progress_pct}%)")


async def mark_job_failed(job_id: str, error: str) -> None:
    sb = get_supabase()
    sb.table("jobs").update({
        "status": "failed",
        "error_message": error[:2000],  # truncar mensagens longas
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "progress_pct": 0,
    }).eq("id", job_id).execute()
    await _append_log(job_id, "error", error[:500])


def check_rate_limit(agency_id: str) -> bool:
    """
    Retorna True se a agência pode disparar uma nova geração.
    Regras:
      - Máximo 1 job com status='generating' por agency_id (simultâneo)
      - Máximo 10 jobs com status='complete'|'failed' nas últimas 24h
    """
    sb = get_supabase()
    
    # Verificar gerações simultâneas
    running = sb.table("jobs") \
        .select("id", count="exact") \
        .eq("agency_id", agency_id) \
        .eq("status", "generating") \
        .execute()
    
    if running.count and running.count > 0:
        return False
    
    # Verificar limite diário
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    daily = sb.table("jobs") \
        .select("id", count="exact") \
        .eq("agency_id", agency_id) \
        .gte("created_at", cutoff) \
        .execute()
    
    return (daily.count or 0) < 10


def _get_client_token(subdomain: str) -> str:
    """Busca o client_token do cliente pelo subdomain para injetar no HTML gerado."""
    try:
        sb = get_supabase()
        result = sb.table("clientes_perfil") \
            .select("client_token") \
            .eq("subdomain", subdomain) \
            .single() \
            .execute()
        return result.data.get("client_token", "") if result.data else ""
    except Exception:
        return ""

async def run_generation_job(job_id: str, config_data: dict, agency_id: str) -> None:
    """
    Executa o pipeline completo de geração de site de forma assíncrona.
    Estado persistido no Supabase antes de cada step via update_job_step().
    """
    import shutil
    import time
    import threading
    from pathlib import Path
    from core.cloudflare_pages_deploy import deploy_to_cloudflare_pages
    from core.config_loader import load_config, _parse_keyword_csv
    from core.mixer import mix_keywords_locations
    from core.sitemap_generator import generate_sitemap
    from core.gemini_client import GeminiClient
    from core.openai_client import OpenAIClient
    from core.stats_accumulator import StatsAccumulator
    from core.page_generator import generate_all_pages
    from core.validator import validate_site, generate_report
    from core.site_data_builder import build_site_data
    from core.template_injector import inject_template
    from core.imagen_client import GeminiImageClient
    from core.topic_generator import generate_topics, generate_services_data
    from core.output_builder import setup_output_dir, generate_fallback_index
    import json
    import yaml
    import uuid

    try:
        await update_job_step(job_id, "validating", 2)
        _gen_start = datetime.now(timezone.utc)

        # ── Construir config.yaml temporário a partir do config_data ──
        # config_data vem do payload do POST /api/clientes.
        # Precisa ser convertido para o formato esperado por load_config().
        # O campo 'subdomain' no config_data é usado como 'dominio'.
        subdomain = config_data.get("subdomain", "")

        config_dict = {
            'empresa': {
                'client_id': config_data.get('client_id'),
                'nome': config_data.get('empresa_nome', ''),
                'dominio': subdomain,
                'categoria': config_data.get('categoria', ''),
                'telefone_whatsapp': config_data.get('telefone', ''),
                'telefone_ligar': config_data.get('telefone', ''),
                'horario': config_data.get('horario', 'Segunda a Sexta, 8h às 18h'),
                'servicos_manuais': config_data.get('servicos', []),
                'cor_marca': config_data.get('cor_marca', '#2563EB'),
                'endereco': config_data.get('endereco', ''),
                'google_maps_embed': _extract_maps_url(config_data.get('google_maps_url', '')),
            },
            'seo': {
                'palavras_chave': config_data.get('keywords', []),
                'locais': config_data.get('locais', []),
            },
            'theme': {
                'mode': config_data.get('theme_mode', 'auto'),
            },
            'api': {
                'provider': 'openrouter',
                'model': 'deepseek/deepseek-v3.2',
                'max_workers': config_data.get('max_workers', 30),
                'max_retries': 3,
            },
            'leads': {
                # Buscar client_token do Supabase pelo subdomain
                'worker_url': os.environ.get('WORKER_URL', ''),
                'client_token': _get_client_token(subdomain),
            }
        }

        config_path = f"config_{uuid.uuid4().hex[:8]}.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)

        try:
            config = load_config(config_path)
            output_dir = str(Path("output") / subdomain)

            await update_job_step(job_id, "mixing", 5)
            pages = mix_keywords_locations(
                config['seo']['palavras_chave'],
                config['seo']['locais']
            )
            await _append_log(job_id, "info", f"{len(pages)} páginas serão geradas")

            setup_output_dir(output_dir, config)

            await update_job_step(job_id, "sitemap", 10)
            generate_sitemap(pages, config, output_dir)

            # Clientes de IA
            client = None
            try:
                client = OpenAIClient(model='gpt-4o-mini')
            except Exception as e:
                logger.warning("OpenAIClient indisponível: %s", e)

            gemini = None
            try:
                gemini = GeminiClient(model='gemini-2.5-flash')
            except Exception as e:
                logger.warning("GeminiClient indisponível: %s", e)

            accumulator = StatsAccumulator()
            phase1_client = gemini or client

            await update_job_step(job_id, "hero", 15)

            hero_img_path = Path(output_dir) / "hero-image.webp"

            async def _task_hero():
                try:
                    img_client = GeminiImageClient()
                    keywords = config.get('seo', {}).get('palavras_chave', [])
                    await asyncio.to_thread(
                        img_client.generate_hero,
                        config['empresa']['categoria'],
                        config['empresa']['nome'],
                        str(hero_img_path),
                        keywords,
                        config.get('theme', {}).get('mode', 'dark'),
                        phase1_client,
                    )
                    import shutil as _shutil
                    legacy_path = Path(output_dir) / "images" / "hero.webp"
                    legacy_path.parent.mkdir(parents=True, exist_ok=True)
                    if hero_img_path.exists():
                        _shutil.copy2(str(hero_img_path), str(legacy_path))
                except Exception as e:
                    logger.error("Erro ao gerar hero image: %s", e)

            async def _task_home_data():
                return await asyncio.to_thread(build_site_data, config, client, gemini_client=gemini)

            async def _task_topics_and_services():
                t = await asyncio.to_thread(generate_topics, config, phase1_client)
                s = await asyncio.to_thread(generate_services_data, config, phase1_client)
                return t, s

            _hero_result, site_data, (topics, servicos_data) = await asyncio.gather(
                _task_hero(),
                _task_home_data(),
                _task_topics_and_services(),
            )

            await update_job_step(job_id, "home_page", 40)
            try:
                await asyncio.to_thread(
                    inject_template,
                    site_data=site_data,
                    output_dir=output_dir,
                    hero_image_path=str(hero_img_path) if hero_img_path.exists() else None,
                )
            except Exception as e:
                logger.error("Erro na home page: %s. Usando fallback.", e)
                generate_fallback_index(config, output_dir)
                
            # Salvar cache da home page
            if config['empresa'].get('client_id'):
                try:
                    sb = get_supabase()
                    raw_ai = site_data.get("_raw_ai", {})
                    sb.table("pages_cache").upsert({
                        "client_id": config['empresa']['client_id'],
                        "subdomain": subdomain,
                        "page_slug": "home",
                        "page_type": "home",
                        "ai_json": raw_ai
                    }, on_conflict="client_id,page_slug").execute()
                except Exception as e:
                    logger.error("Erro ao salvar cache da home: %s", e)

            if servicos_data:
                dados_js_path = Path(output_dir) / "js" / "dados.js"
                with open(dados_js_path, "a", encoding="utf-8") as f:
                    f.write(f"\nconst _DADOS_SERVICOS = {json.dumps(servicos_data, ensure_ascii=False)};\n")

            await update_job_step(job_id, "subpages", 45)

            # Para jobs assíncronos, usar asyncio.to_thread para não bloquear o event loop
            # O progress_callback atualiza o banco via update_job_step
            total_pages = len(pages)

            async def _run_subpages():
                """Wrapper assíncrono para generate_all_pages (bloqueante)."""
                pages_done = [0]

                def progress_cb(current, total_p, title):
                    pages_done[0] = current
                    # Calcular percentual entre step subpages (45%) e validating_quality (90%)
                    pct = 45 + int((current / max(total_p, 1)) * 45)
                    # Não podemos chamar update_job_step diretamente aqui (thread diferente)
                    # Atualizar apenas o progress_pct no banco via chamada síncrona
                    sb = get_supabase()
                    sb.table("jobs").update({
                        "progress_pct": pct,
                        "step": "subpages",
                    }).eq("id", job_id).execute()

                await asyncio.to_thread(
                    generate_all_pages,
                    pages=pages,
                    config=config,
                    topics=topics,
                    client=client,
                    template_path="templates/page.html",
                    output_dir=output_dir,
                    progress_callback=progress_cb,
                    gemini_client=gemini,
                    stats_accumulator=accumulator,
                )

            await _run_subpages()

            await update_job_step(job_id, "validating_quality", 90)
            results = validate_site(output_dir, config)
            api_stats = accumulator.get_summary()
            generate_report(results, config, api_stats, output_dir)

            # Registrar no histórico
            _gen_end = datetime.now(timezone.utc)
            sb = get_supabase()
            summary = accumulator.get_summary()
            client_id = config_data.get('client_id')
            sb.table("historico_geracao").insert({
                "agency_id":             agency_id,
                "client_id":             client_id,
                "job_id":                job_id,
                "total_pages_generated": results.get('total_pages', 0),
                "valid_pages":           results.get('valid_pages', 0),
                "error_pages":           len(results.get('errors', [])),
                "duration_seconds":      int((_gen_end - _gen_start).total_seconds()),
                "cost_usd":  float(summary.get('total', {}).get('cost_usd', 0)),
                "cost_brl":  float(summary.get('total', {}).get('cost_brl', 0)),
                "tokens_used":    int(summary.get('total', {}).get('tokens', 0)),
                "gemini_tokens":  int(summary.get('gemini', {}).get('input_tokens', 0) +
                                      summary.get('gemini', {}).get('output_tokens', 0)),
                "openai_tokens":  int(summary.get('openai', {}).get('input_tokens', 0) +
                                      summary.get('openai', {}).get('output_tokens', 0)),
            }).execute()

            await update_job_step(job_id, "deploying", 93)
            deploy_url = ""
            if subdomain:
                deploy_url = await deploy_to_cloudflare_pages(subdomain, output_dir)
                sb.table("clientes_perfil").update({
                    "status": "live",
                    "last_generated": datetime.now(timezone.utc).isoformat(),
                }).eq("subdomain", subdomain).execute()

            await update_job_step(job_id, "done", 100, status="complete")
            await _append_log(job_id, "info", f"Deploy concluído: {deploy_url}")

        finally:
            if os.path.exists(config_path):
                os.remove(config_path)

    except Exception as e:
        err = traceback.format_exc()
        logger.error("Job %s falhou: %s", job_id, err)
        await mark_job_failed(job_id, str(e))

async def run_fast_sync_job(job_id: str, config_data: dict, agency_id: str):
    """
    Tier 1.5 Fast Re-render:
    Reconstrói o site inteiro em segundos (< 2 min) usando as informações atualizadas
    do config_data cruzadas com a infraestrutura no `pages_cache`.
    SEM chamadas à IA (bypass).
    """
    import shutil
    from pathlib import Path
    from core.cloudflare_pages_deploy import deploy_to_cloudflare_pages
    from core.site_data_builder import build_site_data
    from core.template_injector import inject_template
    from core.page_generator import _generate_single_page
    from core.sitemap_generator import generate_sitemap
    
    sb = get_supabase()
    
    try:
        await update_job_step(job_id, "queue", 5, "generating")
        await _append_log(job_id, "info", "Iniciando Fast Sync (Tier 1.5) - Bypass na Inteligência Artificial")
        
        client_id = config_data.get('id') or config_data.get('client_id')
        subdomain = config_data.get('subdomain')
        if not client_id or not subdomain:
            raise ValueError(f"Faltam dados essenciais para fast_sync: client_id={client_id}, subdomain={subdomain}")
            
        output_dir = str(Path("output") / subdomain)
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Obter cache do Supabase ("validating" = pré-vôo, step válido na tabela)
        await update_job_step(job_id, "validating", 15)
        res = sb.table("pages_cache").select("*").eq("client_id", client_id).execute()
        cache_data = res.data
        if not cache_data:
            raise ValueError("O cache está vazio. Uma regeneração completa (Tier 2) é necessária.")
            
        # 2. Config Mock
        config_dict = {
            'empresa': {
                'client_id': client_id,
                'nome': config_data.get('empresa_nome', ''),
                'dominio': subdomain,
                'categoria': config_data.get('categoria', ''),
                'telefone_whatsapp': config_data.get('telefone', ''),
                'telefone_ligar': config_data.get('telefone', ''),
                'horario': config_data.get('horario', 'Segunda a Sexta, 8h às 18h'),
                'servicos_manuais': config_data.get('servicos', []),
                'cor_marca': config_data.get('cor_marca', '#2563EB'),
                'endereco': config_data.get('endereco', ''),
                'google_maps_embed': _extract_maps_url(config_data.get('google_maps_url', '')),
            },
            'seo': {
                'palavras_chave': config_data.get('keywords', []),
                'locais': config_data.get('locais', []),
            },
            'theme': {
                'mode': config_data.get('theme_mode', 'auto'),
            },
            'leads': {
                'worker_url': os.environ.get('WORKER_URL', ''),
                'client_token': _get_client_token(subdomain),
            },
            'api': {
                'provider':    os.environ.get('AI_PROVIDER', 'openrouter'),
                'model':       os.environ.get('AI_MODEL', 'deepseek/deepseek-v3.2'),
                'max_workers': config_data.get('max_workers', 30),
                'max_retries': 3,
            },
        }
        
        # 3. Identificar raw_ai_override da home
        home_cache = next((r for r in cache_data if r['page_type'] == 'home'), None)
        if not home_cache:
            raise ValueError("Cache da home não encontrado. Tier 2 requerido.")
            
        # 4. Injetar Home
        await update_job_step(job_id, "home_page", 30)
        site_data = await asyncio.to_thread(build_site_data, config_dict, raw_ai_override=home_cache['ai_json'])
        
        # Manter imagem local hero.jpg de execuções passadas se existir
        hero_img_path = Path(output_dir) / "hero-image.webp"
        
        await asyncio.to_thread(inject_template, site_data, output_dir, str(hero_img_path) if hero_img_path.exists() else None)
        
        # 5. Injetar Subpages
        await update_job_step(job_id, "subpages", 50)
        subpages_cache = [r for r in cache_data if r['page_type'] == 'subpage']
        
        with open("templates/page.html", 'r', encoding='utf-8') as f:
            template = f.read()
        from core.template_renderer import replace_config_vars as _replace_config_vars
        template = _replace_config_vars(template, config_dict)
        
        # Extrair metadados da página de dentro do ai_json._page_meta
        def _extract_page_def(sc: dict) -> dict:
            ai_json  = sc.get('ai_json', {}) or {}
            meta     = ai_json.get('_page_meta', {})
            slug     = sc['page_slug']
            return {
                'title':    meta.get('title', slug),
                'filename': slug + '.html',
                'keyword':  meta.get('keyword', ''),
                'location': meta.get('location', ''),
            }
        
        all_pages_dummy = [_extract_page_def(c) for c in subpages_cache]
        
        async def _run_fast_subpages():
            def f_thread():
                for sc in subpages_cache:
                    page_def = _extract_page_def(sc)
                    # Remove _page_meta do ai_json antes de passar como override
                    ai_json_clean = {k: v for k, v in (sc.get('ai_json') or {}).items() if k != '_page_meta'}
                    _generate_single_page(
                        page=page_def, 
                        all_pages=all_pages_dummy,
                        config=config_dict, 
                        topics={},
                        template=template,
                        output_dir=output_dir,
                        raw_ai_override=ai_json_clean
                    )
            await asyncio.to_thread(f_thread)
            
        await _run_fast_subpages()
        
        # Sitemap
        generate_sitemap(all_pages_dummy, config_dict, output_dir)
        
        # Deploy
        await update_job_step(job_id, "deploying", 80)
        deploy_url = await deploy_to_cloudflare_pages(subdomain, output_dir)
        sb.table("clientes_perfil").update({
            "status": "live",
            "last_generated": datetime.now(timezone.utc).isoformat(),
        }).eq("subdomain", subdomain).execute()
        
        await update_job_step(job_id, "done", 100, status="complete")
        await _append_log(job_id, "info", f"Fast Deploy: {deploy_url}")
        
    except Exception as e:
        err = f"Fast Sync falhou: {str(e)}\n{traceback.format_exc()}"
        logger.error(err)
        await mark_job_failed(job_id, err)
