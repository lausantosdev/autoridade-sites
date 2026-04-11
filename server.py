"""
SiteGen - Backend Server (FastAPI)
Serve o frontend wizard e executa o pipeline via WebSocket
"""
import os
import json
import shutil
import asyncio
import threading
import uuid
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import yaml
import uvicorn
from fastapi import FastAPI, WebSocket, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from core.auth import get_current_agency
from core.supabase_client import get_supabase
from core.job_queue import run_generation_job, check_rate_limit
from core.magic_editor import apply_chat_edit
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config_loader import load_config
from core.mixer import mix_keywords_locations, get_summary
from core.sitemap_generator import generate_sitemap
from core.gemini_client import GeminiClient
from core.topic_generator import generate_topics
from core.openai_client import OpenAIClient
from core.stats_accumulator import StatsAccumulator
from core.page_generator import generate_all_pages, _replace_config_vars
from core.validator import validate_site, generate_report
from core.site_data_builder import build_site_data
from core.template_injector import inject_template
import re
from core.config_loader import _parse_keyword_csv
from core.imagen_client import GeminiImageClient
from core.topic_generator import generate_services_data
from core.output_builder import setup_output_dir, generate_fallback_index
from core.logger import get_logger
logger = get_logger(__name__)


app = FastAPI(title="SiteGen SEO Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://painel.autoridade.digital",  # painel em produção
        "http://localhost:8000",               # desenvolvimento local
        "http://localhost:3000",               # dev frontend alternativo
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check para monitoramento de uptime."""
    return {"status": "ok", "service": "sitegen-cloud"}

# Estado global das gerações
generations = {}

# Garantir que os diretórios de runtime existam (não vão para o git)
Path("output").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)

# Montar diretórios estáticos para visualização dos sites gerados e do painel
app.mount("/out", StaticFiles(directory="output"), name="out")
app.mount("/output", StaticFiles(directory="output"), name="output")
# Nota: /dashboard NÃO é servido como StaticFiles pois o servidor
# injeta as variáveis de ambiente no HTML em tempo de execução.

@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard/", response_class=HTMLResponse)
async def serve_dashboard():
    """
    Serve o painel administrativo injetando as variáveis de ambiente no HTML.
    Os placeholders SUPABASE_URL_AQUI e SUPABASE_ANON_KEY_AQUI são substituídos
    em runtime — nunca ficam com valores reais no arquivo em disco (git-safe).
    """
    dashboard_path = Path("dashboard") / "index.html"
    if not dashboard_path.exists():
        raise HTTPException(404, "Dashboard não encontrado")
    
    html = dashboard_path.read_text(encoding="utf-8")
    
    supabase_url     = os.environ.get("SUPABASE_URL", "")
    supabase_anon    = os.environ.get("SUPABASE_ANON_KEY", "")
    
    html = html.replace("SUPABASE_URL_AQUI", supabase_url)
    html = html.replace("SUPABASE_ANON_KEY_AQUI", supabase_anon)
    
    return HTMLResponse(content=html)


@app.post("/api/auth/reset-password")
async def reset_password(body: dict):
    """
    Envia email de redefinição de senha via Supabase server-side.
    Evita problemas de CORS/DNS ao chamar o Supabase diretamente do browser.
    """
    import httpx
    try:
        email = str(body.get("email") or "").strip()
        if not email:
            return JSONResponse({"ok": False, "error": "Email obrigatório"}, status_code=400)

        supabase_url = os.environ.get("SUPABASE_URL", "")
        service_key  = os.environ.get("SUPABASE_SERVICE_KEY", "")

        if not supabase_url or not service_key:
            return JSONResponse({"ok": False, "error": "Servidor não configurado"}, status_code=500)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{supabase_url}/auth/v1/recover",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "email": email,
                    "options": {"redirect_to": "https://sitegen.onrender.com/dashboard"}
                }
            )

        if resp.status_code in (200, 204):
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": f"Supabase: {resp.text}"}, status_code=400)

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve o frontend wizard."""
    frontend_path = Path("frontend") / "index.html"
    if not frontend_path.exists():
        raise HTTPException(404, "Frontend não encontrado")
    return frontend_path.read_text(encoding='utf-8')


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Recebe upload do CSV de keywords do Google Keyword Planner."""
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    filename = f"keywords_{uuid.uuid4().hex[:8]}.csv"
    filepath = upload_dir / filename
    
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Parse para preview
    keywords = _parse_keyword_csv(str(filepath))
    
    return {
        "success": True,
        "filepath": str(filepath),
        "keywords": keywords,
        "count": len(keywords)
    }


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """WebSocket para geração com progresso em tempo real."""
    await websocket.accept()
    
    try:
        t0 = time.time()
        # Receber configuração do frontend
        data = await websocket.receive_json()
        
        await websocket.send_json({"type": "status", "message": "Iniciando geração..."})
        
        # Criar config.yaml temporário
        config_data = _build_config(data)
        config_path = f"config_{uuid.uuid4().hex[:8]}.yaml"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
        
        try:
            # Carregar e validar config
            await websocket.send_json({"type": "step", "step": 1, "message": "Validando configuração..."})
            config = load_config(config_path)
            
            dominio = config['empresa']['dominio']
            output_dir = str(Path("output") / dominio)
            
            await websocket.send_json({
                "type": "info",
                "message": f"{len(config['seo']['palavras_chave'])} palavras-chave × {len(config['seo']['locais'])} locais"
            })
            
            # Mix
            await websocket.send_json({"type": "step", "step": 2, "message": "Gerando combinações..."})
            await asyncio.sleep(0.05)
            pages = mix_keywords_locations(
                config['seo']['palavras_chave'],
                config['seo']['locais']
            )
            await websocket.send_json({
                "type": "info",
                "message": f"{len(pages)} páginas serão geradas"
            })
            await asyncio.sleep(0.05)
            
            # Setup output
            setup_output_dir(output_dir, config)
            
            # Sitemap
            await websocket.send_json({"type": "step", "step": 3, "message": "Gerando sitemap..."})
            await asyncio.sleep(0.05)
            generate_sitemap(pages, config, output_dir)
            
            # API Clients
            client = None
            try:
                client = OpenAIClient(model='gpt-4o-mini')
                logger.info("OpenAIClient ativo — fallback real pronto")
            except Exception as e:
                logger.warning("OpenAIClient indisponível (%s) — Gemini sem fallback", e)

            # GeminiClient como primário (structured output, mais rápido)
            gemini = None
            try:
                gemini = GeminiClient(model='gemini-2.5-flash')
                logger.info("GeminiClient ativo — usando como primário")
            except Exception as e:
                logger.warning("GeminiClient indisponível (%s)", e)

            # Acumulador de stats por sessão
            accumulator = StatsAccumulator()

            # Projeção pré-geração (enviada para o frontend antes de começar)
            projection = accumulator.get_projection(len(pages), config['api']['max_workers'])
            await websocket.send_json({"type": "projection", **projection})

            # ── Fase paralela: Hero + Home Data + Topics ──────────────
            # As 3 chamadas são independentes entre si e podem rodar em paralelo.
            # Ganho estimado: ~130s por geração (brainstorm opt. 2).
            await websocket.send_json({
                "type": "step", "step": 4,
                "message": "Gerando imagem, home page e inteligência de negócio em paralelo..."
            })
            hero_img_path = Path(output_dir) / "hero-image.jpg"

            # Phase 1 usa Gemini (primário) ou OpenAI (fallback) — nunca None
            phase1_client = gemini or client

            async def _task_hero():
                """Gera imagem hero com Gemini Imagen."""
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
                    legacy_path = Path(output_dir) / "images" / "hero.jpg"
                    legacy_path.parent.mkdir(parents=True, exist_ok=True)
                    if hero_img_path.exists():
                        shutil.copy2(str(hero_img_path), str(legacy_path))
                except Exception as e:
                    logger.error("Erro ao gerar imagem AI: %s", e)

            async def _task_home_data():
                """Gera conteúdo da home page via IA."""
                return await asyncio.to_thread(build_site_data, config, client, gemini_client=gemini)

            async def _task_topics_and_services():
                """Gera tópicos do nicho e dados de serviços."""
                t = await asyncio.to_thread(generate_topics, config, phase1_client)
                s = await asyncio.to_thread(generate_services_data, config, phase1_client)
                return t, s

            # Dispara tudo em paralelo
            _hero_result, site_data, (topics, servicos_data) = await asyncio.gather(
                _task_hero(),
                _task_home_data(),
                _task_topics_and_services(),
            )

            # Injetar home page (precisa de site_data + hero_img_path prontos)
            await websocket.send_json({"type": "step", "step": 5, "message": "Montando home page premium..."})
            try:
                await asyncio.to_thread(
                    inject_template,
                    site_data=site_data,
                    output_dir=output_dir,
                    hero_image_path=str(hero_img_path) if hero_img_path.exists() else None,
                )
            except Exception as e:
                logger.error("Erro na home SiteGen: %s. Usando template fallback.", e)
                generate_fallback_index(config, output_dir)

            # Salvar dados de serviços (se houver)
            if servicos_data:
                dados_js_path = Path(output_dir) / "js" / "dados.js"
                with open(dados_js_path, "a", encoding="utf-8") as f:
                    f.write(f"\nconst _DADOS_SERVICOS = {json.dumps(servicos_data, ensure_ascii=False)};\n")
            
            # Subpáginas SEO
            await websocket.send_json({"type": "step", "step": 6, "message": "Gerando páginas SEO..."})
            
            total = len(pages)
            completed = [0]
            loop = asyncio.get_running_loop()
            progress_queue: asyncio.Queue = asyncio.Queue()

            def progress_cb(current, total_pages, title):
                completed[0] = current
                loop.call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {
                        "type": "progress",
                        "current": current,
                        "total": total_pages,
                        "percentage": round((current / max(total_pages, 1)) * 100),
                        "cost_brl": accumulator.get_live_cost()
                    }
                )

            # Executar geração em thread separada
            def run_generation():
                generate_all_pages(
                    pages=pages,
                    config=config,
                    topics=topics,
                    client=client,
                    template_path="templates/page.html",
                    output_dir=output_dir,
                    progress_callback=progress_cb,
                    gemini_client=gemini,
                    stats_accumulator=accumulator
                )

            # Limite de tempo global para TODA a etapa de geração de páginas.
            # Cada página tem até 6min (page_generator). Com buffer de 10min extra para o ZIP.
            MAX_GENERATION_SECONDS = len(pages) * 360 + 600

            thread = threading.Thread(target=run_generation, daemon=True)
            thread.start()

            # Monitorar progresso via queue (disparo imediato por página concluída)
            deadline = time.time() + MAX_GENERATION_SECONDS
            while thread.is_alive():
                if time.time() > deadline:
                    logger.error(
                        "Geração ultrapassou o deadline de %ds — abortando WebSocket",
                        MAX_GENERATION_SECONDS
                    )
                    await websocket.send_json({
                        "type": "error",
                        "message": "Timeout: a geração demorou mais que o esperado. Tente com menos páginas ou tente novamente."
                    })
                    return  # Fecha o WebSocket, a thread continua em daemon e morre
                try:
                    msg = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    await websocket.send_json(msg)
                except asyncio.TimeoutError:
                    # Heartbeat a cada 1s sem nova página
                    await websocket.send_json({
                        "type": "progress",
                        "current": completed[0],
                        "total": total,
                        "percentage": round((completed[0] / max(total, 1)) * 100)
                    })

            thread.join(timeout=10)  # Espera no máximo 10s extras para flush final

            # Drena mensagens restantes antes de seguir
            while not progress_queue.empty():
                await websocket.send_json(progress_queue.get_nowait())
            
            # Validate
            await websocket.send_json({"type": "step", "step": 7, "message": "Validando qualidade..."})
            results = validate_site(output_dir, config)
            api_stats = accumulator.get_summary()
            generate_report(results, config, api_stats, output_dir)
            
            # ZIP
            await websocket.send_json({"type": "step", "step": 8, "message": "Empacotando site..."})
            zip_path = shutil.make_archive(
                str(Path("output") / f"{dominio}_site"),
                'zip',
                output_dir
            )
            
            # Tempo final
            t1 = time.time()
            elapsed = int(t1 - t0)
            mins, secs = divmod(elapsed, 60)
            duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            
            # Resultado final
            summary = accumulator.get_summary()
            await websocket.send_json({
                "type": "complete",
                "message": "Site gerado com sucesso!",
                "stats": {
                    "pages": results['total_pages'],
                    "valid": results['valid_pages'],
                    "errors": len(results['errors']),
                    "warnings": len(results['warnings']),
                    "words": results['stats'].get('total_words', 0),
                    "cost_usd": summary['total']['cost_usd'],
                    "cost_brl": summary['total']['cost_brl'],
                    "tokens": sum(
                        summary[p].get('input_tokens', 0) + summary[p].get('output_tokens', 0)
                        for p in ('gemini', 'openai')
                    ),
                    "duration": duration_str,
                    "providers": summary
                },
                "download": f"/api/download/{dominio}"
            })
            
        finally:
            # Cleanup config temporário
            if os.path.exists(config_path):
                os.remove(config_path)
                
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()


@app.get("/api/download/{dominio}")
async def download_site(dominio: str):
    """Download do site gerado como ZIP."""
    # Sanitizar: bloquear path traversal
    if '..' in dominio or '/' in dominio or '\\' in dominio:
        raise HTTPException(400, "Domínio inválido")
    zip_path = Path("output") / f"{dominio}_site.zip"
    if not zip_path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(
        str(zip_path),
        media_type='application/zip',
        filename=f"{dominio}_site.zip"
    )


def _build_config(data: dict) -> dict:
    """Constrói config.yaml a partir dos dados do frontend."""
    # Parse keywords
    keywords = []
    if data.get('keywords_csv_path'):
        keywords = _parse_keyword_csv(data['keywords_csv_path'])
    
    if data.get('keywords_manual'):
        manual = [k.strip() for k in data['keywords_manual'].split('\n') if k.strip()]
        keywords.extend(manual)
    
    # Parse locations
    locations = [l.strip() for l in data.get('locations', '').split('\n') if l.strip()]
    
    google_maps_input = data.get('google_maps', '')
    if '<iframe' in google_maps_input:
        match = re.search(r'src="([^"]+)"', google_maps_input)
        if match:
            google_maps_input = match.group(1)
            
    return {
        'empresa': {
            'nome': data.get('empresa_nome', ''),
            'dominio': data.get('dominio', ''),
            'categoria': data.get('categoria', ''),
            'telefone_whatsapp': data.get('telefone', ''),
            'telefone_ligar': data.get('telefone', ''),
            'horario': data.get('horario', 'Segunda a Sexta, 8h às 18h'),
            'servicos_manuais': [s.strip() for s in data.get('servicos', '').split('\n') if s.strip()],
            'cor_marca': data.get('cor_marca', '#2563EB'),
            'endereco': data.get('endereco', ''),
            'google_maps_embed': google_maps_input,
        },
        'seo': {
            'palavras_chave': keywords,
            'locais': locations,
        },
        'theme': {
            'mode': data.get('theme_mode', 'auto')
        },
        'api': {
            'provider': 'openrouter',
            'model': data.get('model', 'deepseek/deepseek-v3.2'),
            'max_workers': int(data.get('max_workers', 30)),
            'max_retries': 3,
        },
        'leads': {
            # Na versão cloud, worker_url vem das variáveis de ambiente
            # e client_token é gerado automaticamente pelo Supabase.
            # O wizard não coleta mais esses campos do usuário.
            'worker_url':   os.environ.get('WORKER_URL', ''),
            'client_token': data.get('client_token', ''),  # ainda usado no fluxo WebSocket local
        }
    }

# ── API Cloud: Clientes ───────────────────────────────────────

@app.get("/api/clientes")
async def list_clientes(agency=Depends(get_current_agency)):
    """Lista todos os clientes da agência com métricas básicas."""
    agency_id = agency["sub"]
    sb = get_supabase()
    
    result = sb.table("clientes_perfil") \
        .select("id, empresa_nome, subdomain, custom_domain, site_url, status, last_generated, cor_marca, categoria") \
        .eq("agency_id", agency_id) \
        .order("created_at", desc=True) \
        .execute()
    
    return {"clientes": result.data}

@app.post("/api/clientes")
async def create_cliente(data: dict, agency=Depends(get_current_agency)):
    """Cria um novo perfil de cliente e dispara geração."""
    agency_id = agency["sub"]
    
    # Validação mínima
    required = ["empresa_nome", "subdomain", "categoria", "telefone", "keywords", "locais"]
    for field in required:
        if not data.get(field):
            raise HTTPException(400, f"Campo obrigatório: {field}")
            
    import re
    subdomain = re.sub(r"[^a-z0-9\-]", "", data["subdomain"].lower())
    if len(subdomain) < 3:
        raise HTTPException(400, "subdomain deve ter ao menos 3 caracteres válidos")
    
    sb = get_supabase()
    
    cliente = sb.table("clientes_perfil").insert({
        "agency_id":       agency_id,
        "empresa_nome":    data["empresa_nome"],
        "subdomain":       subdomain,
        "categoria":       data["categoria"],
        "cor_marca":       data.get("cor_marca", "#2563EB"),
        "servicos":        data.get("servicos", []),
        "telefone":        data["telefone"],
        "endereco":        data.get("endereco", ""),
        "google_maps_url": data.get("google_maps_url"),
        "horario":         data.get("horario", "Segunda a Sexta, 8h às 18h"),
        "keywords":        data["keywords"],
        "locais":          data["locais"],
        "theme_mode":      data.get("theme_mode", "auto"),
        "max_workers":     data.get("max_workers", 30),
    }).execute()
    
    client_id = cliente.data[0]["id"]
    
    job = sb.table("jobs").insert({
        "agency_id": agency_id,
        "client_id": client_id,
        "status":    "pending",
        "step":      "queue",
    }).execute()
    
    job_id = job.data[0]["id"]
    
    config_data = {**data, "subdomain": subdomain, "agency_id": agency_id}
    asyncio.create_task(run_generation_job(job_id, config_data, agency_id))
    
    return {
        "cliente_id": client_id,
        "job_id":     job_id,
        "message":    f"Geração iniciada — acompanhe em /api/jobs/{job_id}/status",
    }

@app.get("/api/clientes/{cliente_id}")
async def get_cliente(cliente_id: str, agency=Depends(get_current_agency)):
    agency_id = agency["sub"]
    sb = get_supabase()
    result = sb.table("clientes_perfil") \
        .select("*") \
        .eq("id", cliente_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(404, "Cliente não encontrado")
    return result.data

@app.post("/api/clientes/{client_id}/chat-edit")
async def chat_edit_cliente(
    client_id: str,
    data: dict,
    agency=Depends(get_current_agency),
):
    instruction = data.get("instruction", "").strip()
    if not instruction:
        raise HTTPException(400, "instruction não pode ser vazio")
    
    agency_id = agency["sub"]
    
    gemini = None
    try:
        from core.gemini_client import GeminiClient
        gemini = GeminiClient(model='gemini-2.5-flash')
    except Exception as e:
        raise HTTPException(500, f"IA Indisponivel: {e}")
        
    try:
        result = await apply_chat_edit(client_id, agency_id, instruction, gemini)
    except (ValueError, PermissionError) as e:
        raise HTTPException(400 if isinstance(e, ValueError) else 403, str(e))
    
    if result.get("changed"):
        sb = get_supabase()
        profile = result["profile"]
        
        job = sb.table("jobs").insert({
            "agency_id": agency_id,
            "client_id": client_id,
            "status":    "pending",
            "step":      "queue",
        }).execute()
        
        job_id = job.data[0]["id"]
        config_data = {**profile, "subdomain": profile["subdomain"]}
        asyncio.create_task(run_generation_job(job_id, config_data, agency_id))
        
        result["job_id"] = job_id
    
    return result

# ── API Cloud: Jobs ───────────────────────────────────────────

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str, agency=Depends(get_current_agency)):
    agency_id = agency["sub"]
    sb = get_supabase()
    
    result = sb.table("jobs") \
        .select("id, status, step, progress_pct, error_message, started_at, finished_at, logs") \
        .eq("id", job_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Job não encontrado")
    
    job = result.data
    job["logs"] = job.get("logs", [])[-20:]
    return job

@app.get("/api/jobs")
async def list_jobs(agency=Depends(get_current_agency)):
    agency_id = agency["sub"]
    sb = get_supabase()
    result = sb.table("jobs") \
        .select("id, status, step, progress_pct, created_at, finished_at, client_id, error_message") \
        .eq("agency_id", agency_id) \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()
    return {"jobs": result.data}

# ── API Cloud: Leads e Relatórios ─────────────────────────────

@app.get("/api/leads")
async def list_leads(
    client_token: str = None,
    limit: int = 100,
    agency=Depends(get_current_agency),
):
    agency_id = agency["sub"]
    sb = get_supabase()
    
    query = sb.table("leads").select("*").order("created_at", desc=True).limit(min(limit, 500))
    
    if client_token:
        query = query.eq("client_token", client_token)
    else:
        tokens_result = sb.table("clientes_perfil").select("client_token").eq("agency_id", agency_id).execute()
        tokens = [r["client_token"] for r in tokens_result.data]
        if tokens:
            query = query.in_("client_token", tokens)
        else:
            return {"leads": [], "total": 0}
            
    result = query.execute()
    return {"leads": result.data, "total": len(result.data)}

@app.get("/api/historico")
async def list_historico(agency=Depends(get_current_agency)):
    agency_id = agency["sub"]
    sb = get_supabase()
    result = sb.table("historico_geracao") \
        .select("*, clientes_perfil(empresa_nome, subdomain)") \
        .eq("agency_id", agency_id) \
        .order("created_at", desc=True) \
        .limit(100) \
        .execute()
    return {"historico": result.data}

if __name__ == "__main__":
    print("\n--- SiteGen - Server ---")
    print("   Abra http://localhost:8000 no navegador\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
