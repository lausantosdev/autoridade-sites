js = open('template-dist/assets/index-BYtPjAsq.js', 'r').read()

# Extrair 2000 chars ao redor de featuresSection
idx = js.find('featuresSect')
start = max(0, idx - 100)
end = min(len(js), idx + 2000)
print(js[start:end])
