import re

js = open('template-dist/assets/index-BYtPjAsq.js', 'r').read()

# Buscar a area ao redor de "featuresSection" ou "features"
for term in ['featuresSect', 'features', 'servico', 'Servic']:
    idx = js.find(term)
    if idx >= 0:
        start = max(0, idx-200)
        end = min(len(js), idx+500)
        print(f"=== Found '{term}' at {idx} ===")
        print(js[start:end])
        print()

# Buscar "bg-accent" e "rounded" juntos para encontrar o container do grid
for m in re.finditer(r'bg-accent', js):
    start = max(0, m.start()-200)
    end = min(len(js), m.end()+200)
    ctx = js[start:end]
    if 'rounded' in ctx or 'grid' in ctx or 'overflow' in ctx:
        print(f"=== bg-accent + rounded/grid/overflow at {m.start()} ===")
        print(ctx)
        print()
