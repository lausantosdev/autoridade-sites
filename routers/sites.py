"""
Router: Sites Gerados
Rotas: listagem, detalhe e magic-edit de sites gerados (tabela sites_gerados).
"""
import json
import re as _re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from core.auth import get_current_agency
from core.supabase_client import get_supabase
from core.gemini_client import GeminiClient
from core.cloudflare_pages_deploy import deploy_to_cloudflare_pages
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Campos editáveis via Magic Edit em sites_gerados
_ALLOWED_SITE_PATHS = {
    "/empresa_nome", "/categoria", "/telefone",
    "/status",  # permite marcar como 'live' ou 'zip_only'
}

_SYSTEM_PROMPT_SITE = """Você é o editor de registros de sites do SiteGen.
Interprete a instrução e retorne um JSON Object com os campos a atualizar.
Retorne APENAS o JSON. Campos permitidos: empresa_nome, categoria, telefone, status.
Exemplo: {"empresa_nome": "Novo Nome Ltda", "categoria": "Energia Solar"}
Se não houver alteração: {}
"""


@router.get("/sites")
async def list_sites(agency=Depends(get_current_agency), q: str = None):
    """Lista todos os sites gerados, com deploy_url e link para ZIP."""
    sb = get_supabase()
    query = sb.table("sites_gerados") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(200)

    result = query.execute()
    sites = result.data or []

    # Filtro de busca server-side (complementa o filtro JS client-side)
    if q:
        q_lower = q.lower()
        sites = [
            s for s in sites
            if q_lower in (s.get("empresa_nome") or "").lower()
            or q_lower in (s.get("subdomain") or "").lower()
            or q_lower in (s.get("categoria") or "").lower()
        ]

    return {"sites": sites, "total": len(sites)}


@router.get("/sites/{site_id}")
async def get_site(site_id: str, agency=Depends(get_current_agency)):
    """Retorna dados de um site gerado pelo ID."""
    sb = get_supabase()
    result = sb.table("sites_gerados").select("*").eq("id", site_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Site não encontrado")
    return result.data


@router.post("/sites/{site_id}/magic-edit")
async def magic_edit_site(
    site_id: str,
    body: dict,
    agency=Depends(get_current_agency),
):
    """
    Edita um site gerado via instrução em linguagem natural.
    A IA interpreta a instrução, atualiza os metadados em sites_gerados,
    regera o site completo e faz novo deploy no Cloudflare Pages.
    Retorna deploy_url atualizado.
    """
    instruction = (body.get("instruction") or "").strip()
    if not instruction:
        raise HTTPException(400, "instruction não pode ser vazio")

    sb = get_supabase()

    # 1. Buscar registro existente
    row_result = sb.table("sites_gerados").select("*").eq("id", site_id).single().execute()
    if not row_result.data:
        raise HTTPException(404, "Site não encontrado")
    site = row_result.data
    subdomain = site["subdomain"]

    # 2. Inicializar cliente IA
    try:
        gemini = GeminiClient(model='gemini-2.5-flash')
    except Exception as e:
        raise HTTPException(500, f"IA indisponível: {e}")

    # 3. Pedir patch à IA
    prompt = f"{_SYSTEM_PROMPT_SITE}\n\nRegistro atual:\n{json.dumps(site, ensure_ascii=False, indent=2)}\n\nInstrução: {instruction}"

    try:
        resp = gemini.generate_content(prompt)
        raw = resp.text
        json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
        updates = json.loads(json_match.group()) if json_match else {}
    except Exception as ai_err:
        raise HTTPException(500, f"Erro na IA: {ai_err}")

    # 4. Aplicar updates permitidos
    safe_updates = {k: v for k, v in updates.items() if f"/{k}" in _ALLOWED_SITE_PATHS}
    if safe_updates:
        sb.table("sites_gerados").update(safe_updates).eq("id", site_id).execute()
        logger.info("Magic edit site %s: %s", subdomain, list(safe_updates.keys()))

    # 5. Republicar o site com a config atual (carrega do disco output/<subdomain>)
    output_dir = str(Path("output") / subdomain)
    new_deploy_url = site.get("deploy_url")

    if Path(output_dir).exists():
        try:
            new_deploy_url = await deploy_to_cloudflare_pages(subdomain, output_dir)
            deploy_status = "live"
            sb.table("sites_gerados").update({
                "deploy_url": new_deploy_url,
                "status":     deploy_status,
            }).eq("id", site_id).execute()
            logger.info("Re-deploy após magic-edit: %s → %s", subdomain, new_deploy_url)
        except Exception as deploy_err:
            logger.warning("Re-deploy falhou: %s", deploy_err)
    else:
        logger.warning("output_dir não existe para %s — deploy pulado", subdomain)

    return {
        "ok":            True,
        "updated_fields": list(safe_updates.keys()),
        "deploy_url":    new_deploy_url,
        "message":       f"{len(safe_updates)} campo(s) atualizado(s). Site republicado." if safe_updates else "Nenhuma alteração nos metadados. Site republicado.",
    }
