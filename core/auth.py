"""
Validação de tokens JWT emitidos pelo Supabase Auth.
Usa a função get_user nativa do Supabase para validação agnóstica de algoritmo
(compatível com HS256, ES256 e futuras rotações de chaves).
"""
import logging
from fastapi import Header, HTTPException, status
from core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

async def get_current_agency(authorization: str = Header(...)) -> dict:
    """
    Dependency FastAPI. Valida o Bearer token JWT nativamente na API do Supabase.
    Delegar ao Supabase garante compatibilidade com qualquer algoritmo (HS256/ES256)
    e respeita revogações de sessão em tempo real.
    Retorna dicionário com 'sub' (agency_id UUID) compatível com o sistema.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou mal formatado",
        )
    
    token = authorization.removeprefix("Bearer ")
    sb = get_supabase()
    
    try:
        response = sb.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou sessão não encontrada",
            )
        return {"sub": response.user.id, "email": response.user.email}

    except HTTPException:
        raise  # Propagar HTTPExceptions sem modificar

    except Exception as e:
        # Pode ser erro de rede com o Supabase — logar para diagnóstico
        logger.error("Erro ao validar token com Supabase: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação temporariamente indisponível",
        )
