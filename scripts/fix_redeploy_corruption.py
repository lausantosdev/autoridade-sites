# -*- coding: utf-8 -*-
"""Corrige a corrupção na função redeployCliente causada por edição errada."""

CORRUPTED = (
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    alert(`\xe2\x9a\xa1 Fast Redeploy iniciado! Job ID: ${data.job_id}\\nAcompanhe na aba Jobs.`);\r\n"
    b"                    method: 'POST',\r\n"
    b"                    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }\r\n"
    b"                });\r\n"
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    openProgressModal(data.job_id, clienteId, empresaNome);\r\n"
    b"                } else {\r\n"
    b"                    alert('\xe2\x9d\x8c Erro: ' + (data.detail || JSON.stringify(data)));\r\n"
    b"                }\r\n"
    b"            } catch(e) {\r\n"
    b"                alert('\xe2\x9d\x8c Erro de rede: ' + e.message);\r\n"
    b"            }\r\n"
    b"        }\r\n"
    b"\r\n"
    b"\n"
)

FIXED = (
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    alert(`\xe2\x9a\xa1 Fast Redeploy iniciado! Job ID: ${data.job_id}\\nAcompanhe na aba Jobs.`);\r\n"
    b"                    switchTab('jobs');\r\n"
    b"                } else {\r\n"
    b"                    alert('\xe2\x9d\x8c ' + (data.detail || JSON.stringify(data)));\r\n"
    b"                }\r\n"
    b"            } catch(e) {\r\n"
    b"                alert('\xe2\x9d\x8c Erro de rede: ' + e.message);\r\n"
    b"            }\r\n"
    b"        }\r\n"
    b"\r\n"
    b"        async function regenerarCliente(clienteId, empresaNome) {\r\n"
    b"            if (!confirm(`Regenerar o site de \"${empresaNome}\" completamente? Isso vai criar um novo job e pode levar ~10-15 min.`)) return;\r\n"
    b"\r\n"
    b"            const token = _session?.access_token;\r\n"
    b"            try {\r\n"
    b"                const resp = await fetch(`${API_BASE}/api/clientes/${clienteId}/regenerar`, {\r\n"
    b"                    method: 'POST',\r\n"
    b"                    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }\r\n"
    b"                });\r\n"
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    openProgressModal(data.job_id, clienteId, empresaNome);\r\n"
    b"                } else {\r\n"
    b"                    alert('\xe2\x9d\x8c Erro: ' + (data.detail || JSON.stringify(data)));\r\n"
    b"                }\r\n"
    b"            } catch(e) {\r\n"
    b"                alert('\xe2\x9d\x8c Erro de rede: ' + e.message);\r\n"
    b"            }\r\n"
    b"        }\r\n"
    b"\r\n"
    b"\n"
)

with open('dashboard/index.html', 'rb') as f:
    content = f.read()

if CORRUPTED in content:
    content2 = content.replace(CORRUPTED, FIXED, 1)
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print('OK - corrupção corrigida')
else:
    print('PADRAO CORROMPIDO NAO ENCONTRADO - verificar manualmente')
    idx = content.find(b'redeployCliente')
    print(repr(content[idx:idx+800]))
