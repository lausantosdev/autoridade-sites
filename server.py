"""
Autoridade Sites - Backend Server (FastAPI)
Serve o frontend wizard e executa o pipeline via WebSocket
"""
import os
import json
import shutil
import asyncio
import threading
import uuid
import time
from pathlib import Path
from datetime import datetime

import yaml
import uvicorn
from fastapi import FastAPI, WebSocket, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config_loader import load_config
from core.mixer import mix_keywords_locations, get_summary
from core.sitemap_generator import generate_sitemap
from core.openrouter_client import OpenRouterClient
from core.topic_generator import generate_topics
from core.page_generator import generate_all_pages, _replace_config_vars
from core.validator import validate_site, generate_report


app = FastAPI(title="Autoridade Sites SEO Generator")

# Estado global das gerações
generations = {}

# Montar diretórios estáticos para visualização dos sites gerados
app.mount("/out", StaticFiles(directory="output"), name="out")
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve o frontend wizard."""
    frontend_path = Path("frontend") / "index.html"
    if not frontend_path.exists():
        raise HTTPException(404, "Frontend não encontrado")
    return frontend_path.read_text(encoding='utf-8')


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Recebe upload do CSV de keywords do Google Keyword Planner."""
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    filename = f"keywords_{uuid.uuid4().hex[:8]}.csv"
    filepath = upload_dir / filename
    
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Parse para preview
    from core.config_loader import _parse_keyword_csv
    keywords = _parse_keyword_csv(str(filepath))
    
    return {
        "success": True,
        "filepath": str(filepath),
        "keywords": keywords,
        "count": len(keywords)
    }


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """WebSocket para geração com progresso em tempo real."""
    await websocket.accept()
    
    try:
        t0 = time.time()
        # Receber configuração do frontend
        data = await websocket.receive_json()
        
        await websocket.send_json({"type": "status", "message": "Iniciando geração..."})
        
        # Criar config.yaml temporário
        config_data = _build_config(data)
        config_path = f"config_{uuid.uuid4().hex[:8]}.yaml"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
        
        try:
            # Carregar e validar config
            await websocket.send_json({"type": "step", "step": 1, "message": "Validando configuração..."})
            config = load_config(config_path)
            
            dominio = config['empresa']['dominio']
            output_dir = str(Path("output") / dominio)
            
            await websocket.send_json({
                "type": "info",
                "message": f"{len(config['seo']['palavras_chave'])} palavras-chave × {len(config['seo']['locais'])} locais"
            })
            
            # Mix
            await websocket.send_json({"type": "step", "step": 2, "message": "Gerando combinações..."})
            await asyncio.sleep(0.05)
            pages = mix_keywords_locations(
                config['seo']['palavras_chave'],
                config['seo']['locais']
            )
            await websocket.send_json({
                "type": "info",
                "message": f"{len(pages)} páginas serão geradas"
            })
            await asyncio.sleep(0.05)
            
            # Setup output
            _setup_output(output_dir, config)
            
            # Sitemap
            await websocket.send_json({"type": "step", "step": 3, "message": "Gerando sitemap..."})
            await asyncio.sleep(0.05)
            generate_sitemap(pages, config, output_dir)
            
            # Index
            await websocket.send_json({"type": "step", "step": 4, "message": "Criando página principal..."})
            await asyncio.sleep(0.05)
            _generate_index(config, output_dir)
            
            # API Client
            client = OpenRouterClient(
                model=config['api']['model'],
                max_retries=config['api']['max_retries']
            )
            
            # Topics & Services
            await websocket.send_json({"type": "step", "step": 5, "message": "Gerando inteligência de negócio..."})
            await asyncio.sleep(0.05)
            topics = await asyncio.to_thread(generate_topics, config, client)
            
            from core.topic_generator import generate_services_data
            servicos_data = await asyncio.to_thread(generate_services_data, config, client)
            if servicos_data:
                dados_js_path = Path(output_dir) / "js" / "dados.js"
                with open(dados_js_path, "a", encoding="utf-8") as f:
                    f.write(f"\nconst _DADOS_SERVICOS = {json.dumps(servicos_data, ensure_ascii=False)};\n")
            
            # Pages
            await websocket.send_json({"type": "step", "step": 6, "message": "Gerando páginas SEO..."})
            await asyncio.sleep(0.05)
            
            total = len(pages)
            completed = [0]
            
            def progress_cb(current, total_pages, title):
                completed[0] = current
                # Envia progresso via thread-safe queue (simplificado para agora)
            
            # Executar geração em thread separada
            def run_generation():
                generate_all_pages(
                    pages=pages,
                    config=config,
                    topics=topics,
                    client=client,
                    template_path="templates/page.html",
                    output_dir=output_dir,
                    progress_callback=progress_cb
                )
            
            thread = threading.Thread(target=run_generation)
            thread.start()
            
            # Monitorar progresso
            while thread.is_alive():
                await asyncio.sleep(2)
                await websocket.send_json({
                    "type": "progress",
                    "current": completed[0],
                    "total": total,
                    "percentage": round((completed[0] / max(total, 1)) * 100)
                })
            
            thread.join()
            
            # Validate
            await websocket.send_json({"type": "step", "step": 7, "message": "Validando qualidade..."})
            results = validate_site(output_dir, config)
            api_stats = client.get_stats()
            generate_report(results, config, api_stats, output_dir)
            
            # ZIP
            await websocket.send_json({"type": "step", "step": 8, "message": "Empacotando site..."})
            zip_path = shutil.make_archive(
                str(Path("output") / f"{dominio}_site"),
                'zip',
                output_dir
            )
            
            # Tempo final
            t1 = time.time()
            elapsed = int(t1 - t0)
            mins, secs = divmod(elapsed, 60)
            duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            
            # Resultado final
            await websocket.send_json({
                "type": "complete",
                "message": "Site gerado com sucesso!",
                "stats": {
                    "pages": results['total_pages'],
                    "valid": results['valid_pages'],
                    "errors": len(results['errors']),
                    "warnings": len(results['warnings']),
                    "words": results['stats'].get('total_words', 0),
                    "cost_usd": api_stats['cost_usd'],
                    "cost_brl": api_stats['cost_brl'],
                    "tokens": api_stats['total_tokens'],
                    "duration": duration_str,
                },
                "download": f"/api/download/{dominio}"
            })
            
        finally:
            # Cleanup config temporário
            if os.path.exists(config_path):
                os.remove(config_path)
                
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()


@app.get("/api/download/{dominio}")
async def download_site(dominio: str):
    """Download do site gerado como ZIP."""
    zip_path = Path("output") / f"{dominio}_site.zip"
    if not zip_path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(
        str(zip_path),
        media_type='application/zip',
        filename=f"{dominio}_site.zip"
    )


def _build_config(data: dict) -> dict:
    """Constrói config.yaml a partir dos dados do frontend."""
    # Parse keywords
    keywords = []
    if data.get('keywords_csv_path'):
        from core.config_loader import _parse_keyword_csv
        keywords = _parse_keyword_csv(data['keywords_csv_path'])
    
    if data.get('keywords_manual'):
        manual = [k.strip() for k in data['keywords_manual'].split('\n') if k.strip()]
        keywords.extend(manual)
    
    # Parse locations
    locations = [l.strip() for l in data.get('locations', '').split('\n') if l.strip()]
    
    import re
    google_maps_input = data.get('google_maps', '')
    if '<iframe' in google_maps_input:
        match = re.search(r'src="([^"]+)"', google_maps_input)
        if match:
            google_maps_input = match.group(1)
            
    return {
        'empresa': {
            'nome': data.get('empresa_nome', ''),
            'dominio': data.get('dominio', ''),
            'categoria': data.get('categoria', ''),
            'telefone_whatsapp': data.get('telefone', ''),
            'telefone_ligar': data.get('telefone', ''),
            'horario': data.get('horario', 'Segunda a Sexta, 8h às 18h'),
            'servicos_manuais': [s.strip() for s in data.get('servicos', '').split('\n') if s.strip()],
            'cor_marca': data.get('cor_marca', '#2563EB'),
            'google_maps_embed': google_maps_input,
        },
        'seo': {
            'palavras_chave': keywords,
            'locais': locations,
        },
        'api': {
            'provider': 'openrouter',
            'model': data.get('model', 'deepseek/deepseek-chat'),
            'max_workers': int(data.get('max_workers', 30)),
            'max_retries': 3,
        }
    }


def _setup_output(output_dir: str, config: dict):
    """Copia assets do template para o output e cria o JS de dados."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    templates = Path("templates")
    for subdir in ['css', 'js', 'images']:
        src = templates / subdir
        dst = output_path / subdir
        if src.exists() and not dst.exists():
            shutil.copytree(str(src), str(dst))

    # Processar variáveis no arquivo CSS copiado
    css_path = output_path / "css" / "style.css"
    if css_path.exists():
        from core.page_generator import _replace_config_vars
        css_content = css_path.read_text(encoding='utf-8')
        css_content = _replace_config_vars(css_content, config)
        css_path.write_text(css_content, encoding='utf-8')

    # Criar js/dados.js dinamicamente com base nas configurações
    from core.config_loader import get_whatsapp_link, get_phone_display

    dados_js = {
        "empresa_nome": config['empresa']['nome'],
        "empresa_categoria": config['empresa']['categoria'],
        "telefone_whatsapp": config['empresa']['telefone_whatsapp'],
        "telefone_link": f"tel:{config['empresa']['telefone_whatsapp']}",
        "telefone_display": get_phone_display(config),
        "whatsapp_link": get_whatsapp_link(config),
        "horario": config['empresa'].get('horario', ''),
        "google_maps_url": config['empresa'].get('google_maps_embed', ''),
        "dominio": config['empresa']['dominio'],
        "ano": str(datetime.now().year)
    }

    js_dst = output_path / "js"
    js_dst.mkdir(parents=True, exist_ok=True)
    dados_path = js_dst / "dados.js"
    
    script_content = f"// Criado automaticamente - Autoridade Sites\n"
    script_content += f"const DadosSite = {json.dumps(dados_js, indent=4, ensure_ascii=False)};\n"
    
    with open(dados_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
        
    # Generate index.html after setting up dirs
    _generate_index(config, output_dir)


def _generate_index(config: dict, output_dir: str):
    """Gera a index.html a partir do template."""
    from core.page_generator import _replace_config_vars
    index_template = Path("templates") / "index.html"
    if index_template.exists():
        content = index_template.read_text(encoding='utf-8')
        content = _replace_config_vars(content, config)
        output_path = Path(output_dir) / "index.html"
        output_path.write_text(content, encoding='utf-8')


if __name__ == "__main__":
    print("\n🚀 Autoridade Sites - Server")
    print("   Abra http://localhost:8000 no navegador\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
