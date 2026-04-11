"""
Deploy automático para Cloudflare Pages via Wrangler CLI.

ARQUITETURA MULTI-TENANT:
  Cada cliente tem seu próprio projeto Pages:
    projeto: {subdomain}  (ex: "desentupidorarapidas")
    URL Pages: {subdomain}.pages.dev
    custom domain: {subdomain}.autoridade.digital

  FLUXO DE DNS:
    1. Buscamos o Zone ID de "autoridade.digital" via API (sem env var extra)
    2. Criamos CNAME específico: {subdomain} → {subdomain}.pages.dev
       (registro específico sobrepõe o wildcard *.autoridade.digital)
    3. Registramos o custom domain no projeto Pages
    
  O wildcard existente (*.autoridade.digital → autoridade-digital.pages.dev)
  serve apenas de fallback para subdomínios sem CNAME específico.

VARIÁVEIS DE AMBIENTE NECESSÁRIAS:
  CLOUDFLARE_API_TOKEN    → Token com Pages:Edit + Zone:DNS:Edit
  CLOUDFLARE_ACCOUNT_ID   → ID da conta Cloudflare (32 hex chars)
"""
import os
import asyncio
import subprocess
import aiohttp
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

BASE_DOMAIN = "autoridade.digital"


def _env() -> tuple[str, str]:
    return (
        os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        os.environ.get("CLOUDFLARE_API_TOKEN", ""),
    )


async def deploy_to_cloudflare_pages(subdomain: str, output_dir: str) -> str:
    """
    Deploya o site para um projeto Pages isolado por cliente.
    Cria CNAME DNS específico e registra custom domain automaticamente.
    """
    account_id, api_token = _env()

    if not api_token or not account_id:
        raise RuntimeError(
            "CF Pages: CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN não configurados no Render."
        )

    output_path = Path(output_dir)
    if not output_path.exists() or not any(output_path.iterdir()):
        logger.warning("[CF Deploy] output_dir vazio: %s — pulando deploy", output_dir)
        return f"https://{subdomain}.{BASE_DOMAIN}"

    project_name = subdomain
    file_count   = len(list(output_path.rglob("*")))
    logger.info("[CF Deploy] Deploy: project=%s | files=%d", project_name, file_count)

    # ── 1. Criar projeto Pages do cliente se não existir ──────────────
    await _ensure_project_exists(project_name, account_id, api_token)

    # ── 2. Wrangler: publica arquivos no projeto do cliente ───────────
    await _wrangler_deploy(output_path, project_name, account_id, api_token)

    # ── 3. DNS: CNAME específico  {subdomain} → {subdomain}.pages.dev ─
    #    (sobrepõe wildcard, permite verificação do custom domain)
    zone_id = await _get_zone_id(BASE_DOMAIN, api_token)
    if zone_id:
        cname_target = f"{subdomain}.pages.dev"
        await _upsert_cname(subdomain, cname_target, zone_id, api_token)
    else:
        logger.warning("[CF Deploy] Zone ID não encontrado para %s — DNS não atualizado", BASE_DOMAIN)

    # ── 4. Registrar custom domain no projeto Pages ───────────────────
    await _register_pages_domain(project_name, subdomain, account_id, api_token)

    site_url = f"https://{subdomain}.{BASE_DOMAIN}"
    logger.info("[CF Deploy] ✅ Deploy concluído: %s", site_url)
    return site_url


# ─── helpers ─────────────────────────────────────────────────────────────────

async def _ensure_project_exists(project_name: str, account_id: str, api_token: str) -> None:
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"name": project_name, "production_branch": "main"}, headers=headers) as r:
            if r.status == 409:
                logger.info("[CF Deploy] Projeto '%s' já existe", project_name)
            elif r.status in (200, 201):
                logger.info("[CF Deploy] Projeto '%s' criado", project_name)
            else:
                body = await r.text()
                logger.warning("[CF Deploy] Criar projeto: %s — %s", r.status, body[:200])


async def _wrangler_deploy(output_path: Path, project_name: str, account_id: str, api_token: str) -> None:
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
            subprocess.run, cmd, capture_output=True, text=True, env=env,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        logger.info("[CF Deploy] Wrangler stdout: %s", (stdout or "(vazio)")[-1500:])
        if stderr:
            logger.warning("[CF Deploy] Wrangler stderr: %s", stderr[-500:])
        if result.returncode != 0:
            raise RuntimeError(
                f"Wrangler falhou (exit {result.returncode})\n"
                f"stdout: {stdout[-800:]}\nstderr: {stderr[-400:]}"
            )
    except FileNotFoundError:
        raise RuntimeError("npx/Node.js não encontrado no Render.")


async def _get_zone_id(domain: str, api_token: str) -> str | None:
    """Busca o Zone ID para o domínio via CF API (sem precisar de env var extra)."""
    headers = {"Authorization": f"Bearer {api_token}"}
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://api.cloudflare.com/client/v4/zones",
            params={"name": domain}, headers=headers,
        ) as r:
            data = await r.json()
            zones = data.get("result", [])
            if zones:
                zone_id = zones[0]["id"]
                logger.info("[CF Deploy] Zone ID de '%s': %s", domain, zone_id)
                return zone_id
            logger.warning("[CF Deploy] Zone não encontrada para '%s'", domain)
            return None


async def _upsert_cname(name: str, target: str, zone_id: str, api_token: str) -> None:
    """Cria ou atualiza CNAME {name}.autoridade.digital → {target} (sobrepõe wildcard)."""
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    dns_api = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

    async with aiohttp.ClientSession() as s:
        # Verificar se já existe
        async with s.get(
            dns_api,
            params={"name": f"{name}.{BASE_DOMAIN}", "type": "CNAME"},
            headers=headers,
        ) as r:
            existing = (await r.json()).get("result", [])

        payload = {"type": "CNAME", "name": name, "content": target, "proxied": True, "ttl": 1}

        if existing:
            record_id = existing[0]["id"]
            async with s.put(f"{dns_api}/{record_id}", json=payload, headers=headers) as r:
                status = "atualizado" if r.status in (200, 201) else f"erro {r.status}"
        else:
            async with s.post(dns_api, json=payload, headers=headers) as r:
                status = "criado" if r.status in (200, 201) else f"erro {r.status}"

        logger.info("[CF Deploy] CNAME %s.%s → %s: %s", name, BASE_DOMAIN, target, status)


async def _register_pages_domain(
    project_name: str, subdomain: str, account_id: str, api_token: str,
) -> None:
    """Vincula {subdomain}.autoridade.digital ao projeto Pages do cliente."""
    custom_domain = f"{subdomain}.{BASE_DOMAIN}"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/pages/projects/{project_name}/domains"
    )
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"name": custom_domain}, headers=headers) as r:
            if r.status == 409:
                logger.info("[CF Deploy] Custom domain já registrado: %s", custom_domain)
            elif r.status in (200, 201):
                logger.info("[CF Deploy] Custom domain registrado: %s", custom_domain)
            else:
                body = await r.text()
                logger.warning("[CF Deploy] Custom domain %s: %s — %s", r.status, custom_domain, body[:200])
