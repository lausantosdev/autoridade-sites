"""
Deploy automático para Cloudflare Pages via Wrangler CLI.

Usa `npx wrangler pages deploy` em vez de implementar a API diretamente.
O Wrangler já lida com todo o handshake de JWT, upload de assets e finalização.
Node.js e npx são pré-instalados nos containers Python do Render.
"""
import os
import asyncio
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CF_ACCOUNT_ID   = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN    = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CF_PROJECT_NAME = os.environ.get("CLOUDFLARE_PAGES_PROJECT", "autoridade-digital")


async def deploy_to_cloudflare_pages(subdomain: str, output_dir: str) -> str:
    """
    Faz deploy do site em output_dir para o projeto Pages via Wrangler CLI.
    Retorna a URL pública do deployment.
    """
    output_path = Path(output_dir)
    if not output_path.exists() or not any(output_path.iterdir()):
        logger.warning("[CF Deploy] output_dir vazio ou inexistente: %s — pulando deploy", output_dir)
        return f"https://{subdomain}.autoridade.digital"

    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        raise RuntimeError(
            "CF Pages: variáveis de ambiente incompletas. "
            "Configure CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN no Render."
        )

    logger.info(
        "[CF Deploy] Iniciando Wrangler deploy: project=%s subdomain=%s files=%d",
        CF_PROJECT_NAME, subdomain, len(list(output_path.rglob("*")))
    )

    cmd = [
        "npx", "--yes", "wrangler@latest",
        "pages", "deploy", str(output_path.resolve()),
        "--project-name", CF_PROJECT_NAME,
        "--branch", "main",
        "--commit-dirty", "true",
    ]

    env = {
        **os.environ,
        "CLOUDFLARE_API_TOKEN":  CF_API_TOKEN,
        "CLOUDFLARE_ACCOUNT_ID": CF_ACCOUNT_ID,
        # Desabilitar telemetria e interatividade
        "WRANGLER_SEND_METRICS": "false",
        "CI": "true",
    }

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            env=env,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        logger.info("[CF Deploy] Wrangler stdout: %s", stdout[-1000:] if stdout else "(vazio)")
        if stderr:
            logger.warning("[CF Deploy] Wrangler stderr: %s", stderr[-500:])

        if result.returncode != 0:
            raise RuntimeError(
                f"Wrangler falhou (exit {result.returncode})\n"
                f"stdout: {stdout[-800:]}\n"
                f"stderr: {stderr[-400:]}"
            )

        # Extrair URL do output do Wrangler
        site_url = _extract_deploy_url(stdout, subdomain)
        logger.info("[CF Deploy] Deploy concluído: %s", site_url)

        # Registrar custom domain (continua usando a API v4 — endpoint simples, não falha)
        await _register_custom_domain(subdomain)

        return site_url

    except FileNotFoundError:
        raise RuntimeError(
            "Wrangler (npx) não encontrado. "
            "Verifique se Node.js está instalado no ambiente Render."
        )


def _extract_deploy_url(wrangler_output: str, subdomain: str) -> str:
    """Extrai a URL de deploy do output do Wrangler CLI."""
    for line in wrangler_output.splitlines():
        line = line.strip()
        if "pages.dev" in line and "http" in line:
            # Linha típica: "✨ Deployment complete! Take a peek over at https://abc123.autoridade-digital.pages.dev"
            parts = line.split()
            for part in parts:
                if part.startswith("http") and "pages.dev" in part:
                    return part.rstrip(".")
    return f"https://{subdomain}.autoridade.digital"


async def _register_custom_domain(subdomain: str) -> None:
    """Registra o custom domain via CF API (melhor-esforço — não falha o deploy)."""
    try:
        import aiohttp
        custom_domain = f"{subdomain}.autoridade.digital"
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
            f"/pages/projects/{CF_PROJECT_NAME}/domains"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"},
                json={"name": custom_domain},
            ) as resp:
                if resp.status == 409:
                    logger.info("[CF Deploy] Custom domain já registrado: %s", custom_domain)
                elif resp.status in (200, 201):
                    logger.info("[CF Deploy] Custom domain registrado: %s", custom_domain)
                else:
                    body = await resp.text()
                    logger.warning("[CF Deploy] Aviso domain: %s — %s", resp.status, body[:200])
    except Exception as e:
        logger.warning("[CF Deploy] Erro ao registrar custom domain (não crítico): %s", e)
