"""
Router: Jobs
Rotas: status de jobs, listagem de jobs, último relatório de geração.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.auth import get_current_agency
from core.supabase_client import get_supabase

router = APIRouter()


@router.get("/jobs/{job_id}/status")
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
    job["logs"] = (job.get("logs") or [])[-20:]  # None-safe slice
    return job


@router.get("/jobs")
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


@router.get("/clientes/{client_id}/ultimo-relatorio")
async def get_ultimo_relatorio(client_id: str, agency=Depends(get_current_agency)):
    """
    Retorna o último historico_geracao do cliente.
    Se não houver registro (ex: cliente criado via Fast Sync/Redeploy sem geração completa),
    retorna 200 com dados vazios em vez de 404 para não quebrar o modal do dashboard.
    """
    agency_id = agency["sub"]
    sb = get_supabase()

    # Buscar subdomain do cliente
    cliente = sb.table("clientes_perfil") \
        .select("subdomain,empresa_nome") \
        .eq("id", client_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    if not cliente.data:
        raise HTTPException(404, "Cliente não encontrado")

    result = sb.table("historico_geracao") \
        .select("*") \
        .eq("client_id", client_id) \
        .eq("agency_id", agency_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not result.data:
        # Sem histórico ainda — retorna placeholder para o modal exibir versão simples
        return {
            "client_id":             client_id,
            "subdomain":             cliente.data["subdomain"],
            "empresa_nome":          cliente.data["empresa_nome"],
            "total_pages_generated": None,
            "valid_pages":           None,
            "error_pages":           None,
            "duration_seconds":      None,
            "cost_brl":              None,
            "tokens_used":           None,
            "gemini_tokens":         None,
            "openai_tokens":         None,
            "created_at":            None,
            "_no_history":           True,
        }

    rel = result.data[0]
    rel["subdomain"] = cliente.data["subdomain"]
    return rel
