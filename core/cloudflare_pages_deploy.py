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

    # ── 2.5 Obter o hostname real .pages.dev gerado pela Cloudflare ──
    actual_pages_domain = await _get_project_subdomain(project_name, account_id, api_token)

    # ── 3. DNS: CNAME específico  {subdomain} → {actual_pages_domain} ─
    #    (sobrepõe wildcard, permite verificação do custom domain)
    zone_id = await _get_zone_id(BASE_DOMAIN, api_token)
    if zone_id:
        await _upsert_cname(subdomain, actual_pages_domain, zone_id, api_token)
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


async def _get_project_subdomain(project_name: str, account_id: str, api_token: str) -> str:
    """Busca o subdomínio real *.pages.dev alocado pela Cloudflare para o projeto."""
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{project_name}"
    
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                subdomain = data.get("result", {}).get("subdomain")
                if subdomain:
                    return subdomain
            
            logger.warning("[CF Deploy] Falha ao obter subdomain real de %s. Usando fallback.", project_name)
            return f"{project_name}.pages.dev"


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
    """
    Vincula {subdomain}.autoridade.digital ao projeto Pages do cliente.
    Se o domínio já estava registrado em estado quebrado (err/pending de tentativa anterior),
    deleta e re-registra para forçar re-verificação com o CNAME novo.
    """
    custom_domain = f"{subdomain}.{BASE_DOMAIN}"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    base_url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/pages/projects/{project_name}/domains"
    )

    async with aiohttp.ClientSession() as s:
        # ── Tentar registrar ───────────────────────────────────────────
        async with s.post(base_url, json={"name": custom_domain}, headers=headers) as r:
            body = await r.text()
            status = r.status
            logger.info("[CF Deploy] POST domain %s → HTTP %s: %s", custom_domain, status, body[:300])

            if status in (200, 201):
                logger.info("[CF Deploy] ✅ Custom domain registrado: %s", custom_domain)
                return

            if status == 409:
                # Domínio já existia — pode estar em estado de erro da tentativa anterior
                # Buscar o registro atual para ver o status de verificação
                logger.info("[CF Deploy] Domain 409 — verificando status atual de %s", custom_domain)
                async with s.get(base_url, headers=headers) as gr:
                    gdata = await gr.json()
                    existing = gdata.get("result", [])
                    domain_rec = next((d for d in existing if d.get("name") == custom_domain), None)

                if domain_rec:
                    dom_status = domain_rec.get("status", "unknown")
                    logger.info("[CF Deploy] Status do domain '%s': %s", custom_domain, dom_status)

                    if dom_status in ("active",):
                        logger.info("[CF Deploy] ✅ Domain já ativo — nada a fazer")
                        return

                    # Status quebrado (error, blocked, pending) → forçar re-verificação
                    logger.warning(
                        "[CF Deploy] Domain em estado '%s' — deletando e re-registrando", dom_status
                    )
                    del_url = f"{base_url}/{custom_domain}"
                    async with s.delete(del_url, headers=headers) as dr:
                        logger.info("[CF Deploy] DELETE domain → HTTP %s", dr.status)
                else:
                    logger.warning("[CF Deploy] 409 mas domain não encontrado na lista — re-tentando")

                # Re-registrar após delete
                await asyncio.sleep(2)
                async with s.post(base_url, json={"name": custom_domain}, headers=headers) as r2:
                    body2 = await r2.text()
                    logger.info(
                        "[CF Deploy] Re-registro domain %s → HTTP %s: %s",
                        custom_domain, r2.status, body2[:200]
                    )
            else:
                logger.warning(
                    "[CF Deploy] ⚠️ Erro ao registrar domain %s: HTTP %s — %s",
                    custom_domain, status, body[:300]
                )


async def delete_client_resources(subdomain: str) -> dict:
    """
    Remove todos os recursos Cloudflare de um cliente deletado:
      - Projeto Pages: DELETE /pages/projects/{subdomain}
      - DNS CNAME: DELETE /zones/{zone}/dns_records/{id}
    Operação melhor-esforço: erros são registrados mas não lançados.
    Retorna dict com status de cada operação.
    """
    account_id, api_token = _env()
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    results = {}

    async with aiohttp.ClientSession() as s:
        # ── 0. Deletar custom domains vinculados ao projeto ───────────
        # A CF retorna erro 8000028 se tentar deletar projeto com custom domains ativos.
        domains_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/pages/projects/{subdomain}/domains"
        )
        domain_delete_errors = []
        try:
            async with s.get(domains_url, headers=headers) as r:
                if r.status == 200:
                    data = await r.json()
                    custom_domains = data.get("result", [])
                    for domain_obj in custom_domains:
                        d_name = domain_obj.get("name")
                        if d_name:
                            del_dom_url = f"{domains_url}/{d_name}"
                            async with s.delete(del_dom_url, headers=headers) as dr:
                                dr_body = await dr.text()
                                logger.info(
                                    "[CF Delete] DELETE custom domain '%s' → HTTP %s: %s",
                                    d_name, dr.status, dr_body[:100]
                                )
                                if dr.status not in (200, 201, 204):
                                    domain_delete_errors.append(f"{d_name}: HTTP {dr.status}")
                    if custom_domains:
                        # Pequeno delay para a CF propagar o unbind antes da exclusão do projeto
                        await asyncio.sleep(1)
                elif r.status == 404:
                    logger.info("[CF Delete] Projeto Pages '%s' não existe — pulando exclusão de domains", subdomain)
                else:
                    body = await r.text()
                    logger.warning("[CF Delete] Erro ao listar domains do projeto '%s': HTTP %s — %s", subdomain, r.status, body[:200])
        except Exception as e:
            logger.warning("[CF Delete] Exceção ao remover custom domains de '%s': %s", subdomain, e)

        if domain_delete_errors:
            results["custom_domains"] = f"erros: {'; '.join(domain_delete_errors)}"
            logger.warning("[CF Delete] Falhas ao desassociar domains antes de deletar projeto: %s", domain_delete_errors)
        else:
            results["custom_domains"] = "limpos"

        # ── 1. Deletar projeto Pages ──────────────────────────────────
        pages_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/pages/projects/{subdomain}"
        )
        async with s.delete(pages_url, headers=headers) as r:
            raw = await r.text()
            logger.info("[CF Delete] DELETE projeto Pages '%s' → HTTP %s: %s", subdomain, r.status, raw[:200])
            if r.status in (200, 201, 204):
                results["pages_project"] = "deletado"
                logger.info("[CF Delete] ✅ Projeto Pages '%s' deletado", subdomain)
            elif r.status == 404:
                results["pages_project"] = "não encontrado (ok)"
                logger.info("[CF Delete] Projeto Pages '%s' não existia", subdomain)
            else:
                results["pages_project"] = f"erro {r.status}: {raw[:100]}"
                logger.warning("[CF Delete] Falha ao deletar projeto Pages '%s': %s", subdomain, raw[:200])

        # ── 2. Deletar CNAME DNS ──────────────────────────────────────
        zone_id = await _get_zone_id(BASE_DOMAIN, api_token)
        if zone_id:
            dns_api = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            # Buscar o record ID
            async with s.get(
                dns_api,
                params={"name": f"{subdomain}.{BASE_DOMAIN}", "type": "CNAME"},
                headers=headers,
            ) as r:
                existing = (await r.json()).get("result", [])

            if existing:
                record_id = existing[0]["id"]
                async with s.delete(f"{dns_api}/{record_id}", headers=headers) as r:
                    if r.status in (200, 201):
                        results["dns_cname"] = "deletado"
                        logger.info("[CF Delete] CNAME %s.%s deletado", subdomain, BASE_DOMAIN)
                    else:
                        body = await r.text()
                        results["dns_cname"] = f"erro {r.status}"
                        logger.warning("[CF Delete] Falha ao deletar CNAME: %s", body[:200])
            else:
                results["dns_cname"] = "não encontrado (ok)"
        else:
            results["dns_cname"] = "zone não encontrada"

    return results
