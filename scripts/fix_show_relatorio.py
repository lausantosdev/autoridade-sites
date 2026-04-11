# -*- coding: utf-8 -*-
"""Substitui showRelatorio para tratar 404 com modal simplificado - v2"""

# Usa um marcador simples que sabemos que é único
ANCHOR_START = b'async function showRelatorio(clienteId, empresaNome) {'
ANCHOR_END   = b'\n        }\n\n        function _renderRelatorio'

NEW_FUNC = (
    b'async function showRelatorio(clienteId, empresaNome, subdomain) {\n'
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
    b'                console.warn(\'Relatorio:\', e);\n'
    b'                _renderRelatorioSimples(clienteId, empresaNome, subdomain);\n'
    b'            }\n'
    b'        }\n'
    b'\n'
    b'        function _renderRelatorioSimples(clienteId, empresaNome, subdomain) {\n'
    b'            const slug = subdomain || clienteId;\n'
    b"            document.getElementById('rel-header').innerHTML = `\n"
    b'                <div style="background:linear-gradient(135deg,#7c3aed22,#0f766e22);border-radius:10px;padding:14px 18px;">\n'
    b"                    <div style=\"font-weight:700;font-size:1rem;\">${escapeHtml(empresaNome || '')}</div>\n"
    b'                    <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">\xe2\x9c\x85 Gera\xc3\xa7\xc3\xa3o conclu\xc3\xadda com sucesso!</div>\n'
    b'                </div>`;\n'
    b"            ['rel-pages','rel-tempo','rel-custo','rel-qualidade'].forEach(id => {\n"
    b"                document.getElementById(id).textContent = '\xe2\x80\x94';\n"
    b'            });\n'
    b"            document.getElementById('rel-detalhes').innerHTML = `\n"
    b'                <div style="color:var(--text-muted);padding:8px 0;">O relat\xc3\xb3rio detalhado estar\xc3\xa1 dispon\xc3\xadvel ap\xc3\xb3s a pr\xc3\xb3xima gera\xc3\xa7\xc3\xa3o completa.</div>`;\n'
    b"            document.getElementById('rel-acoes').innerHTML = `\n"
    b'                <a href="https://${escapeHtml(slug)}.autoridade.digital" target="_blank" style="\n'
    b'                    flex:1;padding:12px;background:#7c3aed;color:#fff;border-radius:10px;\n'
    b'                    text-decoration:none;text-align:center;font-weight:600;font-size:0.9rem;">\n'
    b'                    \xf0\x9f\x8c\x90 Ver Site\n'
    b'                </a>\n'
    b'                <button onclick="closeRelatorio()" style="\n'
    b'                    padding:12px 20px;background:var(--bg);border:1px solid var(--border);\n'
    b'                    border-radius:10px;cursor:pointer;font-family:inherit;color:var(--text);">\n'
    b'                    Fechar\n'
    b'                </button>`;\n'
    b"            document.getElementById('relatorio-modal').style.display = 'flex';\n"
    b'        }\n'
    b'\n'
    b'        function _renderRelatorio'
)

with open('dashboard/index.html', 'rb') as f:
    content = f.read()

idx_start = content.find(ANCHOR_START)
idx_end   = content.find(ANCHOR_END)

if idx_start < 0 or idx_end < 0:
    print(f'ERRO: start={idx_start}, end={idx_end}')
else:
    # Keep everything up to 8 spaces before ANCHOR_START (the indentation)
    prefix = content[:idx_start]
    suffix = content[idx_end + len(ANCHOR_END):]  # everything after the old function+separator
    content2 = prefix + NEW_FUNC + suffix
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print(f'OK - showRelatorio substituido (start={idx_start}, end={idx_end})')
