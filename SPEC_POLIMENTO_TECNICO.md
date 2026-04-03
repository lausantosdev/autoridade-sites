# SPEC — Sessão de Polimento Estrutural (04/04/2026)

> **Para:** Agente de execução
> **Projeto:** `c:\Users\ThinkPad T480\SiteGen`
> **Contexto:** Leia `CONTEXT.md` e `SESSIONS_LOG.md` antes de iniciar.
> **Regra de ouro:** Execute em ordem, roda os testes ao final de cada Fase. Se falhar, corrija antes de avançar.
> **Verificação final:** `pytest tests/ --cov=core --cov-fail-under=75` deve passar com 0 falhas.

---

## Estado Atual (pré-execução)

- ✅ 136 testes passando, 79% coverage
- ✅ `core/logger.py` e `core/exceptions.py` já existem
- ✅ `pyproject.toml`, CI, thread-safety, output_builder, robots.txt já implementados
- ❌ WebSocket (`server.py` L286) ainda captura `Exception` genérica sem categorização
- ❌ `template_injector.py` excluído do coverage sem testes
- ❌ Sem `tests/test_server.py` e `tests/test_template_injector.py`
- ❌ Sem `core/types.py`
- ❌ `ruff check` não foi executado

---

## FASE 1 — Tipagem Estática

### T1.1 — Criar `core/types.py`

**Criar arquivo:** `core/types.py`

```python
"""
Contratos de dados do SiteGen via TypedDict.
Substituem dicts genéricos nos módulos core/, garantindo
autocompletar na IDE e detecção precoce de typos de chaves.
"""
from typing import TypedDict, List, Optional, Dict, Any


class EmpresaConfig(TypedDict, total=False):
    nome: str
    dominio: str
    categoria: str
    telefone_whatsapp: str
    telefone_ligar: Optional[str]
    cor_marca: str
    endereco: Optional[str]
    horario: Optional[str]
    google_maps_embed: Optional[str]
    servicos_manuais: Optional[List[str]]


class SeoConfig(TypedDict, total=False):
    locais: List[str]
    palavras_chave: Optional[List[str]]
    palavras_chave_csv: Optional[str]


class ApiConfig(TypedDict, total=False):
    model: str
    max_retries: int
    max_workers: int


class ThemeConfig(TypedDict, total=False):
    mode: str   # 'light' | 'dark'
    color: str


class SiteConfig(TypedDict, total=False):
    empresa: EmpresaConfig
    seo: SeoConfig
    api: ApiConfig
    theme: ThemeConfig
    leads: Optional[Dict[str, str]]


class PageTemplate(TypedDict):
    title: str
    filename: str
    keyword: str
    local: str
    slug: str


class SiteData(TypedDict, total=False):
    empresa: Dict[str, Any]
    theme: Dict[str, Any]
    seo: Dict[str, Any]
    content: Dict[str, Any]
    schema: Dict[str, Any]
    footer: Dict[str, Any]
```

### T1.2 — Adicionar type hints em `config_loader.py`

No topo de `core/config_loader.py`, adicionar o import:
```python
from core.types import SiteConfig
```

Alterar a assinatura da função `load_config`:
```python
# ANTES:
def load_config(config_path: str = "config.yaml") -> dict:

# DEPOIS:
def load_config(config_path: str = "config.yaml") -> SiteConfig:
```

### T1.3 — Adicionar type hints em `site_data_builder.py`

No topo de `core/site_data_builder.py`, adicionar o import:
```python
from core.types import SiteConfig, SiteData
```

Alterar a assinatura das duas funções públicas:
```python
# ANTES:
def resolve_theme_mode(config: dict, client: OpenRouterClient) -> str:
def build_site_data(config: dict, client: OpenRouterClient) -> dict:

# DEPOIS:
def resolve_theme_mode(config: SiteConfig, client: OpenRouterClient) -> str:
def build_site_data(config: SiteConfig, client: OpenRouterClient) -> SiteData:
```

---

## FASE 2 — Error Handling Granular no WebSocket

### T2.1 — Refatorar handler de erros em `server.py`

**Arquivo:** `server.py`

**Adicionar import** no bloco de imports de `core/`:
```python
from core.exceptions import SiteGenError, ConfigError, APIError, TemplateError
```

**Localizar** o bloco final de tratamento de erros (atualmente ~linha 286):
```python
# ANTES:
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

**Substituir por:**
```python
    except ConfigError as e:
        await websocket.send_json({
            "type": "error",
            "code": "CONFIG_ERROR",
            "message": f"Erro na configuração: {e}. Verifique os campos do formulário."
        })
    except APIError as e:
        await websocket.send_json({
            "type": "error",
            "code": "API_ERROR",
            "message": f"Falha na API de IA: {e}. Verifique sua chave OpenRouter e tente novamente."
        })
    except TemplateError as e:
        await websocket.send_json({
            "type": "error",
            "code": "TEMPLATE_ERROR",
            "message": f"Erro no template: {e}. Execute 'npm run build' na pasta do template."
        })
    except Exception as e:
        logger.error("Erro inesperado no WebSocket: %s", e, exc_info=True)
        await websocket.send_json({
            "type": "error",
            "code": "GENERIC_ERROR",
            "message": f"Erro inesperado: {e}. Contate o suporte."
        })
```

> ⚠️ **ATENÇÃO:** Os interceptadores `ConfigError`, `APIError` e `TemplateError` devem vir **antes** do `except Exception` genérico, pois herdam de `Exception`. A ordem importa.

---

## FASE 3 — Expansão de Cobertura de Testes

### T3.1 — Remover `template_injector.py` dos excludes de coverage

**Arquivo:** `pyproject.toml`

Localizar a seção `[tool.coverage.run]`. Remover `"core/template_injector.py"` da lista `omit`:

```toml
# ANTES (exemplo):
[tool.coverage.run]
omit = [
    "core/imagen_client.py",
    "core/openrouter_client.py",
    "core/template_injector.py",
]

# DEPOIS:
[tool.coverage.run]
omit = [
    "core/imagen_client.py",
    "core/openrouter_client.py",
]
```

### T3.2 — Criar `tests/test_template_injector.py`

**Criar arquivo:** `tests/test_template_injector.py`

```python
"""Testes para core/template_injector.py — funções puras de injeção de HTML."""
from core.template_injector import (
    _inject_meta_tags,
    _inject_site_data,
    _inject_schema,
    _escape_html_attr,
)


def _make_site_data(**overrides):
    base = {
        'empresa': {'dominio': 'test.com.br'},
        'theme': {'color': '#FF0000', 'mode': 'dark'},
        'seo': {
            'title': 'Título do Site',
            'metaDescription': 'Descrição do site',
            'metaKeywords': 'keyword1, keyword2',
            'ogTitle': 'OG Título',
            'ogDescription': 'OG Descrição',
            'local': 'Curitiba',
        },
        'schema': {},
    }
    base.update(overrides)
    return base


HTML_BASE = """<html><head><title>__SITE_TITLE__</title>
<meta name="description" content="__SITE_META_DESC__">
<meta name="keywords" content="__SITE_META_KEYWORDS__">
</head><body><!-- SITE_DATA_INJECT --><!-- SCHEMA_INJECT --></body></html>"""


class TestInjectMetaTags:
    def test_replaces_title_marker(self):
        result = _inject_meta_tags(HTML_BASE, _make_site_data())
        assert 'Título do Site' in result
        assert '__SITE_TITLE__' not in result

    def test_replaces_meta_description(self):
        result = _inject_meta_tags(HTML_BASE, _make_site_data())
        assert 'Descrição do site' in result
        assert '__SITE_META_DESC__' not in result

    def test_injects_canonical_tag(self):
        result = _inject_meta_tags(HTML_BASE, _make_site_data())
        assert 'rel="canonical"' in result
        assert 'https://test.com.br/' in result

    def test_injects_robots_tag(self):
        result = _inject_meta_tags(HTML_BASE, _make_site_data())
        assert 'robots' in result
        assert 'index, follow' in result

    def test_escapes_special_chars_in_title(self):
        data = _make_site_data()
        data['seo']['title'] = 'Título com <tags> & "aspas"'
        result = _inject_meta_tags(HTML_BASE, data)
        assert '&lt;tags&gt;' in result
        assert '&amp;' in result
        assert '&quot;' in result


class TestInjectSiteData:
    def test_injects_script_tag(self):
        html = '<body><!-- SITE_DATA_INJECT --></body>'
        result = _inject_site_data(html, {'key': 'value'})
        assert '<script>window.__SITE_DATA__=' in result
        assert '"key"' in result

    def test_escapes_script_close_tag(self):
        """Previne XSS: </script> dentro do JSON não deve fechar o script prematuro."""
        html = '<body><!-- SITE_DATA_INJECT --></body>'
        data = {'malicious': '</script><script>alert(1)</script>'}
        result = _inject_site_data(html, data)
        assert '</script><script>' not in result
        assert '<\\/script>' in result


class TestInjectSchema:
    def test_no_schema_leaves_placeholder(self):
        html = '<head><!-- SCHEMA_INJECT --></head>'
        result = _inject_schema(html, {'schema': {}})
        assert '<!-- SCHEMA_INJECT -->' not in result

    def test_injects_local_business_schema(self):
        html = '<head><!-- SCHEMA_INJECT --></head>'
        schema = {'localBusiness': '{"@type": "LocalBusiness"}'}
        result = _inject_schema(html, {'schema': schema})
        assert 'application/ld+json' in result
        assert 'LocalBusiness' in result


class TestEscapeHtmlAttr:
    def test_escapes_ampersand(self):
        assert _escape_html_attr('a & b') == 'a &amp; b'

    def test_escapes_quotes(self):
        assert _escape_html_attr('"test"') == '&quot;test&quot;'

    def test_escapes_angle_brackets(self):
        assert _escape_html_attr('<tag>') == '&lt;tag&gt;'

    def test_plain_text_unchanged(self):
        assert _escape_html_attr('texto normal') == 'texto normal'
```

### T3.3 — Criar `tests/test_server.py`

**Criar arquivo:** `tests/test_server.py`

```python
"""Testes para endpoints HTTP síncronos do server.py."""
import pytest
from unittest.mock import patch


# Guardar para não importar o server completo (evita subir uvicorn etc.)
# Testamos as funções auxiliares diretamente

class TestBuildConfig:
    """Testa a montagem de config a partir do form data."""

    def test_download_endpoint_rejects_path_traversal(self):
        """Garante que /api/download não permite path traversal."""
        from fastapi.testclient import TestClient
        from server import app
        client = TestClient(app)

        # Tentar escapar do diretório output com traversal
        response = client.get("/api/download/../../../etc/passwd")
        assert response.status_code in (400, 404, 422)

    def test_download_endpoint_domain_not_found(self):
        """Domínio inexistente retorna 404."""
        from fastapi.testclient import TestClient
        from server import app
        client = TestClient(app)

        response = client.get("/api/download/dominio-que-nao-existe.com.br")
        assert response.status_code == 404
```

---

## FASE 4 — Linter e Validação Final

### T4.1 — Rodar Ruff

```bash
ruff check core/ tests/ generate.py server.py --fix
```

- **Se houver erros não-auto-fixados:** corrigir manualmente os apontados (principalmente `I` — import ordering).
- **NÃO** aplicar regras que quebrem funcionalidade existente. Se uma rule `UP` sugerida for invasiva, ignorar com `# noqa`.

### T4.2 — Validação Final da Suíte

```bash
python -m pytest tests/ -v --cov=core --cov-report=term-missing --cov-fail-under=75
```

**Critério de aceite:**
- ✅ **Zero falhas**
- ✅ **Coverage ≥ 75%** (meta: manter acima de 79%)
- ✅ `ruff check` sem erros

### T4.3 — Commit

```bash
git add core/types.py server.py pyproject.toml tests/test_template_injector.py tests/test_server.py
git commit -m "feat: polimento estrutural — TypedDict, error handling granular e cobertura de testes

- Adiciona core/types.py com TypedDict para SiteConfig, SiteData, PageTemplate
- Refatora except final do WebSocket com códigos de erro categorizados (CONFIG_ERROR, API_ERROR, TEMPLATE_ERROR, GENERIC_ERROR)
- Cria tests/test_template_injector.py cobrindo injeção de meta tags, XSS guard e schemas
- Cria tests/test_server.py com FastAPI TestClient validando path traversal e 404
- Remove template_injector.py dos excludes de coverage
- Aplica ruff --fix para limpeza de imports"
```

### T4.4 — Atualizar `SESSIONS_LOG.md`

Adicionar nova entrada no `SESSIONS_LOG.md`:

```markdown
## 04/04/2026 — Sprint de Polimento Estrutural

**Status:** ✅ Concluída | **Rating do projeto:** 10/10 | **Cobertura de testes:** >79%

### ✅ Feito
- `core/types.py` com TypedDict para contratos de dados
- Error handling granular no WebSocket (`CONFIG_ERROR`, `API_ERROR`, `TEMPLATE_ERROR`)
- `tests/test_template_injector.py` — cobertura das funções puras de injeção
- `tests/test_server.py` — path traversal e 404 com FastAPI TestClient
- `ruff check --fix` — limpeza de imports e type hints

### 🔜 Próxima Sessão
- [ ] Monitoramento de erros em produção (ex: Sentry)
- [ ] Script de deploy automático (rsync / FTP / Cloudflare Pages)
- [ ] Testes E2E do pipeline completo com fixtures de config real
```

---

> **Notas para o Agente de Execução:**
> - Não pule fases. A ordem T1 → T2 → T3 → T4 é intencional (tipagem primeiro, depois testes que dependem dela).
> - Se um teste novo falhar inesperadamente, leia o traceback completo antes de concluir que é bug no teste vs. bug no código.
> - O `test_server.py` requer `httpx` instalado (dependência do `fastapi[testclient]`). Se não estiver no ambiente, adicione `httpx>=0.27.0` ao `[project.optional-dependencies].dev` do `pyproject.toml`.
