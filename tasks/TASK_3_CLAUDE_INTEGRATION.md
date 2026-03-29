# TASK 3 — Integração (executar com Claude / modelo forte)

Estas tarefas exigem leitura e entendimento do código existente antes de modificar.
**Dependência:** TASK_1 e TASK_2 devem estar concluídas antes.

---

## Pré-condições

- `cloudflare-worker/index.js` criado (TASK 1)
- `templates/js/widget.js` criado (TASK 2)
- CSS do widget adicionado ao `templates/css/style.css` (TASK 2)

---

## 1. `core/config_loader.py` — Validar campos de leads

Adicionar ao schema de validação do YAML os campos opcionais:

```yaml
leads:
  worker_url: "https://..."   # opcional
  client_token: "uuid"        # opcional
```

Esses campos são opcionais — se ausentes, o widget não é ativado.

**O que fazer:** ler o arquivo atual, identificar onde ficam as validações/defaults, adicionar `leads.worker_url` e `leads.client_token` como campos opcionais com default `""`.

---

## 2. `core/page_generator.py` — Injetar config do widget

Em `_replace_config_vars()`, adicionar ao dict `replacements`:

```python
'{{worker_url}}':    config.get('leads', {}).get('worker_url', ''),
'{{client_token}}':  config.get('leads', {}).get('client_token', ''),
```

---

## 3. `templates/page.html` — Injetar config do widget + carregar script

**Antes de `</body>`**, adicionar (após `<script src="js/main.js"></script>`):

```html
<!-- Widget de Captura de Leads -->
<script>
window.AUTORIDADE_WIDGET = {
  workerUrl: "{{worker_url}}",
  clientToken: "{{client_token}}",
  dominio: "{{dominio}}",
  empresaNome: "{{empresa_nome}}",
  whatsappNumero: "{{telefone_whatsapp}}",
  keyword: "@keyword",
  local: "@local"
};
</script>
<script src="js/widget.js"></script>
```

**Atenção:** `@keyword` e `@local` são substituídos por `_generate_single_page()` em `page_generator.py` — não são placeholders de config, são substituídos na fase de IA. O `{{...}}` é substituído por `_replace_config_vars()`.

---

## 4. `templates/index.html` — Injetar config do widget + carregar script

**Antes de `</body>`**, adicionar (após `<script src="js/main.js"></script>`):

```html
<!-- Widget de Captura de Leads -->
<script>
window.AUTORIDADE_WIDGET = {
  workerUrl: "{{worker_url}}",
  clientToken: "{{client_token}}",
  dominio: "{{dominio}}",
  empresaNome: "{{empresa_nome}}",
  whatsappNumero: "{{telefone_whatsapp}}",
  keyword: "",
  local: ""
};
</script>
<script src="js/widget.js"></script>
```

---

## 5. `server.py` — Adicionar campos no wizard web

Ler o arquivo atual para identificar onde ficam os campos do formulário. Adicionar dois campos na seção de configuração avançada (ou no final do formulário):

- `worker_url`: campo de texto, label "URL do Cloudflare Worker", placeholder `"https://autoridade-leads.SEU-SUBDOMINIO.workers.dev"`, opcional
- `client_token`: campo de texto, label "Client Token (UUID)", placeholder `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`, opcional

Esses campos devem ser incluídos no dict `config` que é passado para `generate_all_pages()`.

---

## 6. `config.yaml` (exemplo/template) — Adicionar seção leads

Adicionar ao final do arquivo de exemplo:

```yaml
leads:
  worker_url: ""        # URL do Cloudflare Worker (deixe vazio para desativar)
  client_token: ""      # Token único deste cliente (UUID)
```

---

## 7. Teste end-to-end

Após todas as modificações:

```bash
python generate.py --config config.yaml --step pages
```

Abrir uma página gerada no browser e verificar:
1. Botão WhatsApp abre o modal ao clicar (se `worker_url` estiver preenchido)
2. Modal coleta nome + WhatsApp
3. Abre WhatsApp após confirmação

---

## Por que estas tarefas precisam de modelo forte

| Tarefa | Motivo |
|--------|--------|
| `config_loader.py` | Precisa entender o schema de validação existente para não quebrar |
| `page_generator.py` | `_replace_config_vars()` tem lógica específica — adicionar no lugar certo |
| Templates | A ordem das substituições `{{...}}` vs `@...` importa para não criar conflito |
| `server.py` | FastAPI + WebSocket com lógica específica — campos devem chegar no dict correto |
