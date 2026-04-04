import json, re
with open('output/petvida.test/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
match = re.search(r'__SITE_DATA__=(.*?)</script>', html)
if match:
    data = json.loads(match.group(1))
    items = data['featuresSection']['items']
    subtitle = data['hero']['subtitle']
    color = data['theme']['color']
    colorText = data['theme']['colorText']
    print(f"Numero de servicos: {len(items)}")
    for i in items:
        print(f"  - {i['title']}")
    words = len(subtitle.split())
    print(f"hero_subtitle ({words} palavras): {subtitle}")
    print(f"theme.color: {color}")
    print(f"theme.colorText: {colorText}")
