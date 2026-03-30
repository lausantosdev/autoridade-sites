import os
import shutil

template_html = "templates/index.html"
template_css = "templates/css/style.css"

out_dir = "output/apple_test"
os.makedirs(out_dir, exist_ok=True)
os.makedirs(f"{out_dir}/css", exist_ok=True)
os.makedirs(f"{out_dir}/js", exist_ok=True)

# Copy CSS
shutil.copy("templates/css/reset.css", f"{out_dir}/css/reset.css")

with open(template_css, "r", encoding="utf-8") as f:
    css = f.read()

# Replace CSS vars
css = css.replace("{{cor_marca}}", "#FFD700") # Dourado Apple Premium
css = css.replace("{{cor_marca_rgb}}", "255, 215, 0")

with open(f"{out_dir}/css/style.css", "w", encoding="utf-8") as f:
    f.write(css)

# Generate JS data mock
with open(f"{out_dir}/js/dados.js", "w", encoding="utf-8") as f:
    f.write('const DadosSite = {"ano": "2026"};')

with open("templates/js/main.js", "r", encoding="utf-8") as f:
    with open(f"{out_dir}/js/main.js", "w", encoding="utf-8") as f2:
        f2.write(f.read())
        
with open("templates/js/widget.js", "r", encoding="utf-8") as f:
    with open(f"{out_dir}/js/widget.js", "w", encoding="utf-8") as f2:
        f2.write(f.read())

# Replace HTML vars
with open(template_html, "r", encoding="utf-8") as f:
    html = f.read()

replacements = {
    "{{empresa_nome}}": "TechMasters Pro",
    "{{empresa_categoria}}": "Consultoria em TI",
    "{{cor_marca}}": "#FFD700",
    "{{cor_marca_rgb}}": "255, 215, 0",
    "{{whatsapp_link}}": "#",
    "{{google_maps_url}}": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3657.197364115167!2d-46.65651928430756!3d-23.56133298468249!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x94ce59a6d36e768b%3A0x8898b1b2f703e390!2sAv.%20Paulista%2C%201000%20-%20Bela%20Vista%2C%20S%C3%A3o%20Paulo%20-%20SP%2C%2001310-100!5e0!3m2!1spt-BR!2sbr!4v1684841964177!5m2!1spt-BR!2sbr",
    "{{telefone_display}}": "(11) 99999-9999",
    "{{horario}}": "Seg-Sex 08:00 as 18:00",
    "{{endereco_footer}}": "<p>Av. Premium, 1000 - São Paulo</p>",
    "{{servicos_footer}}": "<p>Consultoria\\nInfraestrutura\\nSegurança</p>",
    "{{locais_footer}}": "<p>São Paulo\\nCampinas\\nOsasco</p>",
    "{{ano}}": "2026",
    "{{worker_url}}": "",
    "{{client_token}}": "",
    "{{dominio}}": "techmasters.com.br",
    "{{telefone_whatsapp}}": "5511999999999"
}

for k, v in replacements.items():
    html = html.replace(k, v)

with open(f"{out_dir}/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# Test Gemini Image Fetcher
print("🎨 Gerando Imagem Hero Mock com Gemini Imagen 3...")
from core.imagen_client import GeminiImageClient
try:
    img_client = GeminiImageClient()
    img_client.generate_hero("Consultoria em TI", "TechMasters Pro", f"{out_dir}/images/hero.jpg")
except Exception as e:
    print(f"  ⚠ Aviso do Gemini: {e}")
    print("  👉 Baixando fallback do Unsplash para não quebrar o layout.")
    import urllib.request
    urllib.request.urlretrieve(
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1920&q=80", 
        f"{out_dir}/images/hero.jpg"
    )

print("Mock site created at output/apple_test/index.html")
