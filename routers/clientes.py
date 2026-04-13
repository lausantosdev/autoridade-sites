"""
Router: Clientes
Rotas: CRUD de clientes, chat-edit (Magic Editor), redeploy, delete.
"""
import asyncio
import re as _re

from fastapi import APIRouter, Depends, HTTPException
from core.auth import get_current_agency
from core.supabase_client import get_supabase
from core.job_queue import run_generation_job, run_fast_sync_job
from core.magic_editor import apply_chat_edit
from core.utils import extract_maps_url
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/clientes")
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


@router.post("/clientes")
async def create_cliente(data: dict, agency=Depends(get_current_agency)):
    """Cria um novo perfil de cliente e dispara geração."""
    agency_id = agency["sub"]

    # Validação mínima
    required = ["empresa_nome", "subdomain", "categoria", "telefone", "keywords", "locais"]
    for field in required:
        if not data.get(field):
            raise HTTPException(400, f"Campo obrigatório: {field}")

    subdomain = _re.sub(r"[^a-z0-9\-]", "", data["subdomain"].lower())
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
        "google_maps_url": extract_maps_url(data.get("google_maps_url", "")),
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

    config_data = {**data, "subdomain": subdomain, "agency_id": agency_id, "client_id": client_id}
    asyncio.create_task(run_generation_job(job_id, config_data, agency_id))

    return {
        "cliente_id": client_id,
        "job_id":     job_id,
        "message":    f"Geração iniciada — acompanhe em /api/jobs/{job_id}/status",
    }


@router.get("/clientes/{cliente_id}")
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


@router.post("/clientes/{client_id}/chat-edit")
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
        changed_fields = result["changed"]

        # Tier 2 re-render requires AI if core SEO/Content structure is affected
        tier_2_fields = {"keywords", "locais", "servicos", "categoria"}
        needs_tier_2 = any(f in tier_2_fields for f in changed_fields)

        job = sb.table("jobs").insert({
            "agency_id": agency_id,
            "client_id": client_id,
            "status":    "pending",
            "step":      "queue",
        }).execute()

        job_id = job.data[0]["id"]
        config_data = {**profile, "subdomain": profile["subdomain"]}

        if needs_tier_2:
            logger.info("Tier 2 Edit Detected (%s). Disparando fully re-generate.", changed_fields)
            asyncio.create_task(run_generation_job(job_id, config_data, agency_id))
            result["edit_type"] = "tier_2_full_regen"
        else:
            logger.info("Tier 1.5 Edit Detected (%s). Disparando FAST SYNC.", changed_fields)
            asyncio.create_task(run_fast_sync_job(job_id, config_data, agency_id))
            result["edit_type"] = "tier_1.5_fast_sync"

        result["job_id"] = job_id

    return result


@router.post("/clientes/{client_id}/redeploy")
async def redeploy_cliente(client_id: str, agency=Depends(get_current_agency)):
    """
    Redeploy rápido (Tier 1.5) — usa pages_cache sem chamar a IA.
    Ideal para quando a geração passou mas o deploy falhou, ou o usuário
    quer republicar sem alterar o conteúdo.
    """
    agency_id = agency["sub"]
    sb = get_supabase()

    # Buscar o perfil completo do cliente
    result = sb.table("clientes_perfil") \
        .select("*") \
        .eq("id", client_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(404, "Cliente não encontrado")
    profile = result.data

    # Verificar se tem cache
    cache_check = sb.table("pages_cache") \
        .select("id", count="exact") \
        .eq("client_id", client_id) \
        .execute()
    if not cache_check.count or cache_check.count == 0:
        raise HTTPException(400, "Cache vazio — use 'Regenerar' para uma geração completa com IA.")

    # Criar job e disparar fast sync
    job = sb.table("jobs").insert({
        "agency_id": agency_id,
        "client_id": client_id,
        "status":    "pending",
        "step":      "queue",
    }).execute()
    job_id = job.data[0]["id"]

    config_data = {**profile, "client_id": client_id}
    asyncio.create_task(run_fast_sync_job(job_id, config_data, agency_id))

    return {
        "job_id":    job_id,
        "message":   f"Fast Redeploy iniciado — acompanhe em /api/jobs/{job_id}/status",
        "edit_type": "tier_1.5_redeploy",
    }


@router.delete("/clientes/{client_id}")
async def deletar_cliente(client_id: str, agency=Depends(get_current_agency)):
    """
    Deleta PERMANENTEMENTE um cliente e todos os seus recursos:
      - Supabase: clientes_perfil (cascade → pages_cache, set null → jobs/historico)
      - Cloudflare Pages: projeto isolado do cliente
      - Cloudflare DNS: CNAME {subdomain}.autoridade.digital
    """
    from core.cloudflare_pages_deploy import delete_client_resources
    agency_id = agency["sub"]
    sb = get_supabase()

    # Buscar o perfil para obter o subdomain antes de deletar
    result = sb.table("clientes_perfil") \
        .select("id,subdomain,empresa_nome") \
        .eq("id", client_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(404, "Cliente não encontrado")

    perfil = result.data
    subdomain = perfil["subdomain"]

    errors = []
    cf_results = {}

    # 1. Limpar recursos na Cloudflare (melhor-esforço — não bloqueia o delete)
    try:
        cf_results = await delete_client_resources(subdomain)
        logger.info("CF delete results para %s: %s", subdomain, cf_results)
        for k, v in cf_results.items():
            if isinstance(v, str) and "erro" in v.lower():
                errors.append(f"CF {k}: {v}")
    except Exception as e:
        logger.warning("Erro ao limpar CF para %s: %s", subdomain, e)
        errors.append(f"CF cleanup falhou: {e}")
        cf_results = {"error": str(e)}

    # 2. Deletar do Supabase (CASCADE apaga pages_cache automaticamente)
    sb.table("clientes_perfil") \
        .delete() \
        .eq("id", client_id) \
        .eq("agency_id", agency_id) \
        .execute()

    return {
        "deleted":   True,
        "cliente":   perfil["empresa_nome"],
        "subdomain": subdomain,
        "cf_results": cf_results,
        "warnings":  errors or None,
    }
