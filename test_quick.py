"""Quick test - verifica se o sistema está funcional"""
from core.config_loader import load_config
from core.mixer import mix_keywords_locations, get_summary

config = load_config()
print(f"Empresa: {config['empresa']['nome']}")
print(f"Categoria: {config['empresa']['categoria']}")
print(f"Keywords: {len(config['seo']['palavras_chave'])}")
print(f"Locais: {len(config['seo']['locais'])}")

pages = mix_keywords_locations(config['seo']['palavras_chave'], config['seo']['locais'])
print(f"Mix: {get_summary(pages)}")
print(f"Exemplo: {pages[0]['title']} -> {pages[0]['filename']}")
print("OK!")
