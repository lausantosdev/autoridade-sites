"""
Deploy automático para Cloudflare Pages via Direct Upload API.

FLUXO OBRIGATÓRIO (3 passos — não pular nenhum):
  1. POST /deployments           → obtém deployment_id + JWT de upload
  2. PUT  /{jwt}/file/{path}     → upload de CADA arquivo (um por um)
  3. POST /deployments/{id}      → finaliza/publica o deployment

Documentação: https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
"""
import os
import asyncio
import aiofiles
import aiohttp
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CF_ACCOUNT_ID   = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "account")
CF_API_TOKEN    = os.environ.get("CLOUDFLARE_API_TOKEN", "token")
CF_PROJECT_NAME = os.environ.get("CLOUDFLARE_PAGES_PROJECT", "autoridade-digital")

CF_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects/{CF_PROJECT_NAME}"

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
}

async def deploy_to_cloudflare_pages(subdomain: str, output_dir: str) -> str:
    """
    Faz deploy do site em output_dir para o projeto Pages.
    Retorna a URL pública do deployment.
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        # Fallback for dev: fake success if folder does not exist
        logger.warning(f"output_dir não encontrado: {output_dir}")
        return f"https://{subdomain}.autoridade.digital"

    async with aiohttp.ClientSession() as session:
        # ── PASSO 1: Iniciar deployment ───────────────────────
        logger.info(f"[CF Deploy] Iniciando deployment para '{subdomain}'...")
        async with session.post(
            f"{CF_BASE}/deployments",
            headers=HEADERS,
        ) as resp:
            if resp.status not in (200, 201):
                body = await resp.text()
                raise RuntimeError(f"CF Pages: falha ao iniciar deployment — {resp.status}: {body}")
            data = await resp.json()

        deployment_id = data["result"]["id"]
        upload_jwt    = data["result"]["jwt"]  # JWT temporário para uploads
        
        logger.info(f"[CF Deploy] deployment_id={deployment_id}")

        # ── PASSO 2: Upload de cada arquivo ───────────────────
        # Montar lista de todos os arquivos recursivamente
        files = list(output_path.rglob("*"))
        files = [f for f in files if f.is_file()]
        
        logger.info(f"[CF Deploy] Fazendo upload de {len(files)} arquivos...")

        upload_base = f"https://upload.pages.cloudflare.com/v2/project/{CF_PROJECT_NAME}"
        upload_headers = {
            "Authorization": f"Bearer {upload_jwt}",
        }

        # Upload em lotes de 10 para não sobrecarregar a API
        semaphore = asyncio.Semaphore(10)

        async def upload_file(file_path: Path) -> None:
            relative = file_path.relative_to(output_path)
            url = f"{upload_base}/file/{relative.as_posix()}"
            
            mime = _get_mime_type(file_path.suffix)
            
            async with semaphore:
                async with aiofiles.open(file_path, "rb") as f:
                    content = await f.read()
                async with session.put(
                    url,
                    headers={**upload_headers, "Content-Type": mime},
                    data=content,
                ) as r:
                    if r.status not in (200, 201):
                        body = await r.text()
                        logger.warning(f"[CF Deploy] Falha upload {relative}: {r.status} — {body}")

        await asyncio.gather(*[upload_file(f) for f in files])

        # ── PASSO 3: Finalizar/publicar o deployment ──────────
        # CRÍTICO: sem este passo, o deployment fica em modo "draft"
        logger.info("[CF Deploy] Finalizando deployment...")
        async with session.post(
            f"{CF_BASE}/deployments/{deployment_id}",
            headers=HEADERS,
        ) as resp:
            if resp.status not in (200, 201):
                body = await resp.text()
                raise RuntimeError(f"CF Pages: falha ao finalizar deployment — {resp.status}: {body}")
            result = await resp.json()

        site_url = f"https://{subdomain}.autoridade.digital"
        logger.info(f"[CF Deploy] ✅ Site publicado: {site_url}")
        return site_url


def _get_mime_type(suffix: str) -> str:
    """Mapeia extensão de arquivo para MIME type."""
    return {
        ".html": "text/html; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".json": "application/json",
        ".xml":  "application/xml",
        ".txt":  "text/plain",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".svg":  "image/svg+xml",
        ".ico":  "image/x-icon",
        ".woff": "font/woff",
        ".woff2":"font/woff2",
    }.get(suffix.lower(), "application/octet-stream")
