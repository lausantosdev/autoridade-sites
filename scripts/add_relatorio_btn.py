with open('dashboard/index.html', 'rb') as f:
    content = f.read()

old = (
    b'</button>\r\n'
    b'                            <button onclick="deletarCliente'
)
new = (
    b'</button>\r\n'
    b'                            <button onclick="abrirRelatorio(\'${escapeHtml(c.id)}\', \'${escapeHtml(c.empresa_nome)}\')" '
    b'style="padding:4px 10px;font-size:0.78rem;background:#1e3a5f;border:none;border-radius:6px;color:#7dd3fc;cursor:pointer;font-family:inherit;" '
    b'title="Ver relatorio da ultima geracao">\r\n'
    b'                               \xf0\x9f\x93\x8a Relat\xc3\xb3rio\r\n'
    b'                            </button>\r\n'
    b'                            <button onclick="deletarCliente'
)

if old in content:
    content2 = content.replace(old, new, 1)
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print('OK - botao Relatorio adicionado')
else:
    print('PADRAO NAO ENCONTRADO')
    idx = content.find(b'deletarCliente')
    print(repr(content[idx-80:idx+30]))
