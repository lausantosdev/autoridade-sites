"""
Router: Leads e Histórico
Rotas: listagem de leads captados e histórico de gerações.
"""
from fastapi import APIRouter, Depends
from core.auth import get_current_agency
from core.supabase_client import get_supabase

router = APIRouter()


@router.get("/leads")
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


@router.get("/historico")
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
