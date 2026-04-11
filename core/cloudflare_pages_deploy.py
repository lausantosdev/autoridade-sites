"""
Deploy automático para Cloudflare Pages via Wrangler CLI.

ARQUITETURA MULTI-TENANT:
  Cada cliente tem seu próprio projeto Pages:
    projeto: {subdomain}  (e.g. "desentupidorarapida")
    URL:     {subdomain}.pages.dev
    domínio: {subdomain}.autoridade.digital  (via wildcard CNAME já existente)

  O wildcard CNAME *.autoridade.digital → autoridade-digital.pages.dev
  garante que qualquer subdomínio funcione SEM precisar criar DNS por cliente.

VARIÁVEIS DE AMBIENTE NECESSÁRIAS:
  CLOUDFLARE_API_TOKEN    → Token com Cloudflare Pages:Edit
  CLOUDFLARE_ACCOUNT_ID   → ID da conta (32 hex chars)
"""
import os
import asyncio
import subprocess
import aiohttp
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_CF_ACCOUNT_ID   = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
_CF_API_TOKEN    = os.environ.get("CLOUDFLARE_API_TOKEN", "")


def _env() -> tuple[str, str]:
    """Lê as envvars em runtime (pode mudar sem reiniciar o processo)."""
    return (
        os.environ.get("CLOUDFLARE_ACCOUNT_ID", _CF_ACCOUNT_ID),
        os.environ.get("CLOUDFLARE_API_TOKEN", _CF_API_TOKEN),
    )


async def deploy_to_cloudflare_pages(subdomain: str, output_dir: str) -> str:
    """
    Deploya o site para um projeto Pages isolado por cliente.
    Cada subdomain = 1 projeto Pages = conteúdo independente.
    """
    account_id, api_token = _env()

    if not api_token or not account_id:
        raise RuntimeError(
            "CF Pages: variáveis de ambiente incompletas. "
            "Configure CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN no Render."
        )

    output_path = Path(output_dir)
    if not output_path.exists() or not any(output_path.iterdir()):
        logger.warning("[CF Deploy] output_dir vazio: %s — pulando deploy", output_dir)
        return f"https://{subdomain}.autoridade.digital"

    # project_name = subdomain do cliente (projeto isolado por cliente)
    project_name = subdomain
    file_count = len(list(output_path.rglob("*")))
    logger.info("[CF Deploy] Deploy: project=%s files=%d", project_name, file_count)

    # ── 1. Criar projeto Pages se ainda não existir ────────────────────
    await _ensure_project_exists(project_name, account_id, api_token)

    # ── 2. Wrangler deploy para o projeto do cliente ───────────────────
    cmd = [
        "npx", "--yes", "wrangler@latest",
        "pages", "deploy", str(output_path.resolve()),
        "--project-name", project_name,
        "--branch", "main",
        "--commit-dirty", "true",
    ]
    env = {
        **os.environ,
        "CLOUDFLARE_API_TOKEN":  api_token,
        "CLOUDFLARE_ACCOUNT_ID": account_id,
        "WRANGLER_SEND_METRICS": "false",
        "CI": "true",
    }

    try:
        result = await asyncio.to_thread(
            subprocess.run, cmd,
            capture_output=True, text=True, env=env,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        logger.info("[CF Deploy] Wrangler stdout: %s", stdout[-1500:] if stdout else "(vazio)")
        if stderr:
            logger.warning("[CF Deploy] Wrangler stderr: %s", stderr[-500:])
        if result.returncode != 0:
            raise RuntimeError(
                f"Wrangler falhou (exit {result.returncode})\n"
                f"stdout: {stdout[-800:]}\nstderr: {stderr[-400:]}"
            )
    except FileNotFoundError:
        raise RuntimeError("npx/Node.js não encontrado. Verifique o ambiente Render.")

    # ── 3. Registrar custom domain no projeto do cliente ─────────────
    # O wildcard CNAME *.autoridade.digital já existe no DNS,
    # então só precisamos vincular o domínio ao projeto Pages.
    await _register_custom_domain(project_name, subdomain, account_id, api_token)

    site_url = f"https://{subdomain}.autoridade.digital"
    logger.info("[CF Deploy] Site publicado: %s", site_url)
    return site_url


async def _ensure_project_exists(project_name: str, account_id: str, api_token: str) -> None:
    """Cria o projeto Pages para o cliente se ainda não existir."""
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={
            "name": project_name,
            "production_branch": "main",
        }, headers=headers) as resp:
            if resp.status == 409:
                logger.info("[CF Deploy] Projeto '%s' já existe — OK", project_name)
            elif resp.status in (200, 201):
                logger.info("[CF Deploy] Projeto '%s' criado com sucesso", project_name)
            else:
                body = await resp.text()
                logger.warning("[CF Deploy] Aviso ao criar projeto: %s — %s", resp.status, body[:300])


async def _register_custom_domain(
    project_name: str, subdomain: str, account_id: str, api_token: str
) -> None:
    """Registra {subdomain}.autoridade.digital como custom domain do projeto."""
    custom_domain = f"{subdomain}.autoridade.digital"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/pages/projects/{project_name}/domains"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"name": custom_domain}, headers=headers) as resp:
            if resp.status == 409:
                logger.info("[CF Deploy] Custom domain já registrado: %s", custom_domain)
            elif resp.status in (200, 201):
                logger.info("[CF Deploy] Custom domain registrado: %s", custom_domain)
            else:
                body = await resp.text()
                logger.warning("[CF Deploy] Aviso domain: %s — %s", resp.status, body[:200])
