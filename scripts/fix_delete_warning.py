# -*- coding: utf-8 -*-
"""Atualiza mensagem de sucesso do deletarCliente para mostrar avisos do CF."""

OLD = (
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    alert(`\xe2\x9c\x85 \"${empresaNome}\" deletado com sucesso!`);\r\n"
    b"                    await loadClientesTab();\r\n"
    b"                } else {\r\n"
    b"                    alert('\xe2\x9d\x8c Erro: ' + (data.detail || JSON.stringify(data)));\r\n"
    b"                }\r\n"
    b"            } catch(e) {\r\n"
    b"                alert('\xe2\x9d\x8c Erro de rede: ' + e.message);\r\n"
    b"            }\r\n"
    b"        }\r\n"
    b"\r\n"
    b"        // \xe2\x94\x80\xe2\x94\x80 Aba Auditoria"
)

NEW = (
    b"                const data = await resp.json();\r\n"
    b"                if (resp.ok) {\r\n"
    b"                    if (data.warnings && data.warnings.length) {\r\n"
    b"                        alert(\r\n"
    b"                            `\xe2\x9c\x85 \"${empresaNome}\" removido do painel.\\n\\n` +\r\n"
    b"                            `\xe2\x9a\xa0\xef\xb8\x8f Aviso: n\xc3\xa3o foi poss\xc3\xadvel limpar todos os recursos no Cloudflare:\\n` +\r\n"
    b"                            data.warnings.join('\\n') +\r\n"
    b"                            `\\n\\nVoc\xc3\xaa pode deletar manualmente no painel Cloudflare Pages.`\r\n"
    b"                        );\r\n"
    b"                    } else {\r\n"
    b"                        alert(`\xe2\x9c\x85 \"${empresaNome}\" deletado! Projeto Pages e DNS removidos.`);\r\n"
    b"                    }\r\n"
    b"                    await loadClientesTab();\r\n"
    b"                } else {\r\n"
    b"                    alert('\xe2\x9d\x8c Erro: ' + (data.detail || JSON.stringify(data)));\r\n"
    b"                }\r\n"
    b"            } catch(e) {\r\n"
    b"                alert('\xe2\x9d\x8c Erro de rede: ' + e.message);\r\n"
    b"            }\r\n"
    b"        }\r\n"
    b"\r\n"
    b"        // \xe2\x94\x80\xe2\x94\x80 Aba Auditoria"
)

with open('dashboard/index.html', 'rb') as f:
    content = f.read()

if OLD in content:
    content2 = content.replace(OLD, NEW, 1)
    with open('dashboard/index.html', 'wb') as f:
        f.write(content2)
    print('OK - alerta de warnings adicionado ao deletarCliente')
else:
    print('PADRAO NAO ENCONTRADO')
    idx = content.find(b'deletado com sucesso!')
    if idx >= 0:
        print(repr(content[idx-100:idx+200]))
