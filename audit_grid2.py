import re

js = open('template-dist/assets/index-BYtPjAsq.js', 'r').read()

# Encontrar todos os template literals ou strings com classes que contenham 'grid' E 'cols'
# Usando abordagem mais simples
for m in re.finditer(r'grid.cols', js):
    start = max(0, m.start()-300)
    end = min(len(js), m.end()+300)
    ctx = js[start:end]
    print(ctx)
    print('=' * 60)
