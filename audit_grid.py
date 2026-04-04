"""
Audit script: Abre o index.html gerado e extrai informações sobre
a seção de diferenciais para entender a hierarquia de DOM e CSS.
"""
import re, json

html = open('output/petvida.test/index.html', 'r', encoding='utf-8').read()

# O React renderiza no client, mas podemos ver que classes Tailwind são usadas
# pelo CSS bundle. Vamos buscar no JS minificado as classes da grid section.
js = open('template-dist/assets/index-BYtPjAsq.js', 'r', encoding='utf-8').read()

# Procurar padrões que mencionem "grid" junto com classes de layout
grid_patterns = re.findall(r'(?:className|class)[=:]["\']([^"\']*grid[^"\']*)["\']', js)
print("=== Classes com 'grid' no bundle React ===")
for p in set(grid_patterns):
    if len(p) < 200:
        print(f"  {p}")

# Procurar padrões que mencionem "bg-accent" ou backgrounds
bg_patterns = re.findall(r'(?:className|class)[=:]["\']([^"\']*bg-(?:accent|muted|background|card)[^"\']*)["\']', js)
print("\n=== Classes de background no bundle React ===")
for p in set(bg_patterns):
    if len(p) < 200:
        print(f"  {p}")

# Procurar rounded/overflow na area do grid
rounded_patterns = re.findall(r'(?:className|class)[=:]["\']([^"\']*(?:rounded|overflow)[^"\']*grid[^"\']*)["\']', js)
if not rounded_patterns:
    rounded_patterns = re.findall(r'(?:className|class)[=:]["\']([^"\']*grid[^"\']*(?:rounded|overflow)[^"\']*)["\']', js)
print("\n=== Grid + rounded/overflow ===")
for p in set(rounded_patterns):
    if len(p) < 200:
        print(f"  {p}")

# procurar a seção inteira pelo id "diferenciais"
dif_patterns = re.findall(r'["\']diferenciais["\']', js)
print(f"\n=== 'diferenciais' encontrado no JS: {len(dif_patterns)} vezes ===")

# Contexto ao redor
for m in re.finditer(r'diferenciais', js):
    start = max(0, m.start()-100)
    end = min(len(js), m.end()+100)
    ctx = js[start:end]
    print(f"  ...{ctx}...")
