"""
Magic Editor: interpreta comandos em linguagem natural e os converte
em JSON Patches RFC 6902 aplicados de forma segura no perfil do cliente.

SEGURANÇA: a IA nunca acessa campos fora do ALLOWED_PATHS.
"""
import json
from typing import Any
import jsonpatch
from core.supabase_client import get_supabase
import logging

logger = logging.getLogger(__name__)

# Campos editáveis via Chat. Qualquer path fora dessa lista é REJEITADO.
ALLOWED_PATHS = {
    "/empresa_nome",
    "/categoria",
    "/cor_marca",
    "/servicos",
    "/telefone",
    "/endereco",
    "/google_maps_url",
    "/horario",
    "/keywords",
    "/locais",
    "/theme_mode",
    "/max_workers",
}

READONLY_PATHS = {
    "/id", "/created_at", "/agency_id", "/client_token",
    "/subdomain", "/site_url", "/status", "/last_generated",
}

SYSTEM_PROMPT = """Você é o editor de perfis de empresa do SiteGen Cloud.

Sua ÚNICA função é interpretar a instrução do usuário e retornar um JSON Array RFC 6902 com as operações de patch necessárias.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS o JSON Array. Nenhum texto antes ou depois.
2. Use APENAS os paths da lista permitida.
3. Para campos que são arrays (servicos, keywords, locais), use "add" para adicionar itens e "remove" para remover.
4. Para campos simples, use "replace".
5. Nunca use "move", "copy" ou "test".
6. Se a instrução não corresponder a nenhum campo permitido, retorne: []

PATHS PERMITIDOS:
/empresa_nome, /categoria, /cor_marca, /servicos, /telefone,
/endereco, /google_maps_url, /horario, /keywords, /locais, /theme_mode

EXEMPLO:
Instrução: "Mude a cor para azul escuro (#003366) e adicione 'Manutenção Preventiva' aos serviços"
Resposta:
[
  {"op": "replace", "path": "/cor_marca", "value": "#003366"},
  {"op": "add", "path": "/servicos/-", "value": "Manutenção Preventiva"}
]
"""

async def apply_chat_edit(
    client_id: str,
    agency_id: str,
    instruction: str,
    ai_client,  # GeminiClient ou OpenAIClient iterável.
) -> dict:
    sb = get_supabase()
    
    # 1. Buscar perfil
    result = sb.table("clientes_perfil") \
        .select("*") \
        .eq("id", client_id) \
        .eq("agency_id", agency_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise PermissionError(f"Cliente {client_id} não encontrado ou sem permissão")
    
    profile = result.data
    
    # 2. Solicitar patch
    prompt = f"{SYSTEM_PROMPT}\n\nPerfil atual:\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\nInstrução: {instruction}"
    
    raw_response = ""
    try:
        # Se for cliente Gemini existente na app:
        response = ai_client.generate_content(prompt)
        raw_response = response.text
    except Exception:
        # Tenta fallback generico
        pass

    import re
    json_match = re.search(r'\[.*\]', raw_response, re.DOTALL)
    if not json_match:
        raise ValueError("IA não retornou um JSON Array válido")
    patch_ops = json.loads(json_match.group())
    
    if len(patch_ops) == 0:
        return {"message": "Nenhuma alteração necessária", "profile": profile}
    
    for op in patch_ops:
        path = op.get("path", "")
        operation = op.get("op", "")
        if operation not in ("replace", "add", "remove"):
            raise ValueError(f"Operação não permitida: '{operation}'.")
        base_path = "/" + path.strip("/").split("/")[0]
        normalized = "/" + base_path.strip("/")
        if normalized not in ALLOWED_PATHS:
            raise ValueError(f"Campo não editável: '{path}'.")
        if normalized in READONLY_PATHS:
            raise ValueError(f"Campo somente-leitura: '{path}'")
    
    try:
        patch = jsonpatch.JsonPatch(patch_ops)
        updated_profile = patch.apply(profile)
    except jsonpatch.JsonPatchException as e:
        raise ValueError(f"Erro ao aplicar patch: {e}")
    
    changed_fields = {}
    for op in patch_ops:
        base_path = "/" + op["path"].strip("/").split("/")[0]
        field = base_path.strip("/")
        if field in updated_profile:
            changed_fields[field] = updated_profile[field]
    
    if changed_fields:
        sb.table("clientes_perfil").update(changed_fields).eq("id", client_id).execute()
        logger.info(f"Magic edit aplicado para {client_id}: {list(changed_fields.keys())}")
    
    return {
        "message": f"{len(patch_ops)} alteração(ões) aplicada(s)",
        "changed": list(changed_fields.keys()),
        "profile": updated_profile,
    }
