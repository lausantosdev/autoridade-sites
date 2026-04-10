"""
Validação de tokens JWT emitidos pelo Supabase Auth.
O Supabase assina JWTs com HS256 usando o JWT_SECRET do projeto.
"""
import os
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

async def get_current_agency(authorization: str = Header(...)) -> dict:
    """
    Dependency FastAPI. Valida o Bearer token JWT do Supabase.
    Retorna o payload decodificado contendo 'sub' (agency_id UUID).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou mal formatado",
        )
    
    token = authorization.removeprefix("Bearer ")
    
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase não usa 'aud' padrão
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {e}",
        )
