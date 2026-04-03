"""
Output Builder — Setup do diretório de saída (compartilhado entre CLI e Wizard).
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

from core.config_loader import get_whatsapp_link, get_phone_display
from core.template_renderer import replace_config_vars
from core.logger import get_logger
logger = get_logger(__name__)


TEMPLATES_DIR = Path("templates")


def setup_output_dir(output_dir: str, config: dict):
    """Copia assets do template para o output e cria o JS de dados."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Copiar CSS, JS, images
    for subdir in ['css', 'js', 'images']:
        src = TEMPLATES_DIR / subdir
        dst = output_path / subdir
        if src.exists() and not dst.exists():
            shutil.copytree(str(src), str(dst))

    # Processar variáveis no CSS copiado
    css_path = output_path / "css" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding='utf-8')
        css_content = replace_config_vars(css_content, config)
        css_path.write_text(css_content, encoding='utf-8')

    # Criar js/dados.js
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


def generate_fallback_index(config: dict, output_dir: str):
    """Fallback: gera index.html do template HTML puro (caso SiteGen falhe)."""
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        content = index_template.read_text(encoding='utf-8')
        content = replace_config_vars(content, config)
        output_path = Path(output_dir) / "index.html"
        output_path.write_text(content, encoding='utf-8')
        logger.info("Home page fallback gerada (template HTML puro)")
