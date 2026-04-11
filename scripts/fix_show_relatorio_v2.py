# -*- coding: utf-8 -*-
"""
Atualiza showRelatorio para usar _no_history do servidor (nunca mais 404)
"""
OLD = (
    b'        async function showRelatorio(clienteId, empresaNome, subdomain) {\n'
    b'            const token = _session?.access_token;\n'
    b'            try {\n'
    b'                const r = await fetch(`${API_BASE}/api/clientes/${clienteId}/ultimo-relatorio`, {\n'
    b'                    headers: { Authorization: `Bearer ${token}` }\n'
    b'                });\n'
    b'                if (!r.ok) {\n'
    b'                    _renderRelatorioSimples(clienteId, empresaNome, subdomain);\n'
    b'                    return;\n'
    b'                }\n'
    b'                const rel = await r.json();\n'
    b'                _renderRelatorio(rel, clienteId, empresaNome);\n'
    b'            } catch(e) {\n'
    b"                console.warn('Relatorio:', e);\n"
    b'                _renderRelatorioSimples(clienteId, empresaNome, subdomain);\n'
    b'            }\n'
    b'        }\n'
)

NEW = (
    b'        async function showRelatorio(clienteId, empresaNome, subdomain) {\n'
    b'            const token = _session?.access_token;\n'
    b'            try {\n'
    b'                const r = await fetch(`${API_BASE}/api/clientes/${clienteId}/ultimo-relatorio`, {\n'
    b'                    headers: { Authorization: `Bearer ${token}` }\n'
    b'                });\n'
    b'                const rel = r.ok ? await r.json() : {};\n'
    b'                // _no_history = sem geracao completa ainda (so Redeploy/Fast Sync)\n'
    b'                if (!r.ok || rel._no_history) {\n'
    b'                    _renderRelatorioSimples(clienteId, empresaNome, rel.subdomain || subdomain);\n'
    b'                    return;\n'
    b'                }\n'
    b'                _renderRelatorio(rel, clienteId, empresaNome);\n'
    b'            } catch(e) {\n'
    b"                console.warn('Relatorio:', e);\n"
    b'                _renderRelatorioSimples(clienteId, empresaNome, subdomain);\n'
    b'            }\n'
    b'        }\n'
)

with open('dashboard/index.html', 'rb') as f:
    content = f.read()

if OLD in content:
    content2 = content.replace(OLD, NEW, 1)
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print('OK - showRelatorio atualizado para _no_history')
else:
    print('PADRAO NAO ENCONTRADO')
    idx = content.find(b'async function showRelatorio')
    print(repr(content[idx:idx+400]))
