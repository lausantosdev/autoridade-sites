# SPEC — Sessão 1 (03/04/2026): Wizard Web E2E

> **Atividade:** Finalização de Produto — Wizard Web
> **Arquivos principais:** `frontend/index.html`, `tests/test_server.py`
> **Pré-requisito:** `.env` com `OPENROUTER_API_KEY` e `GEMINI_API_KEY` válidas

---

## Fase 1: Bug Fixes

### 1.1 — Corrigir steps desincronizados (frontend × backend)

**Arquivo:** `frontend/index.html`

**Problema:** O backend (`server.py`) envia 9 steps via WebSocket, mas o frontend só exibe 8 items com nomes incorretos a partir do step 4.

**Substituir** (linhas ~733-741) o bloco de `.p-step`:

```html
<!-- ANTES (8 itens, nomes errados) -->
<div class="p-step" data-pstep="1"><i class="fas fa-circle-dot"></i> Validar configuração</div>
<div class="p-step" data-pstep="2"><i class="fas fa-circle-dot"></i> Gerar combinações</div>
<div class="p-step" data-pstep="3"><i class="fas fa-circle-dot"></i> Criar sitemap</div>
<div class="p-step" data-pstep="4"><i class="fas fa-circle-dot"></i> Criar página principal</div>
<div class="p-step" data-pstep="5"><i class="fas fa-circle-dot"></i> Gerar tópicos do nicho</div>
<div class="p-step" data-pstep="6"><i class="fas fa-circle-dot"></i> Gerar páginas SEO</div>
<div class="p-step" data-pstep="7"><i class="fas fa-circle-dot"></i> Validar qualidade</div>
<div class="p-step" data-pstep="8"><i class="fas fa-circle-dot"></i> Empacotar site</div>
```

**Por** (9 itens, nomes alinhados com `server.py` steps 1-9):

```html
<div class="p-step" data-pstep="1"><i class="fas fa-circle-dot"></i> Validar configuração</div>
<div class="p-step" data-pstep="2"><i class="fas fa-circle-dot"></i> Gerar combinações</div>
<div class="p-step" data-pstep="3"><i class="fas fa-circle-dot"></i> Criar sitemap</div>
<div class="p-step" data-pstep="4"><i class="fas fa-circle-dot"></i> Gerar imagem hero</div>
<div class="p-step" data-pstep="5"><i class="fas fa-circle-dot"></i> Criar home page premium</div>
<div class="p-step" data-pstep="6"><i class="fas fa-circle-dot"></i> Gerar inteligência de negócio</div>
<div class="p-step" data-pstep="7"><i class="fas fa-circle-dot"></i> Gerar páginas SEO</div>
<div class="p-step" data-pstep="8"><i class="fas fa-circle-dot"></i> Validar qualidade</div>
<div class="p-step" data-pstep="9"><i class="fas fa-circle-dot"></i> Empacotar site</div>
```

**Substituir** (linhas ~972-982) o mapa `stepPercentages`:

```js
// ANTES
const stepPercentages = {
    1: 5,   // Validar config
    2: 10,  // Gerar combinacoes
    3: 15,  // Criar sitemap
    4: 25,  // Criar imagem hero
    5: 30,  // Home page premium
    6: 35,  // Tópicos do nicho
    7: 40,  // Páginas SEO (começa em 40%)
    8: 90,  // Validar qualidade
    9: 95   // Empacotar site
};
```

```js
// DEPOIS
const stepPercentages = {
    1: 5,
    2: 8,
    3: 12,
    4: 20,   // Gerar imagem hero
    5: 28,   // Home page premium
    6: 35,   // Inteligência de negócio
    7: 40,   // Páginas SEO (começa em 40%)
    8: 90,   // Validar qualidade
    9: 95    // Empacotar site
};
```

> **Nota:** O mapeamento do `type: 'progress'` (páginas SEO) continua correto pois o step 7 = páginas SEO no backend. A fórmula `40 + (pagesProg * 0.45)` não precisa mudar.

---

### 1.2 — Corrigir modelo hardcoded

**Arquivo:** `frontend/index.html`, linha ~933

**Substituir:**
```js
model: 'deepseek/deepseek-chat',
```

**Por:**
```js
model: 'deepseek/deepseek-v3.2',
```

---

### 1.3 — Adicionar `ws.onclose` e botão de retry

**Arquivo:** `frontend/index.html`

**Após** o bloco `ws.onerror` (linha ~954-956), adicionar:

```js
ws.onclose = (event) => {
    if (!event.wasClean) {
        document.getElementById('progressStatus').innerHTML =
            '❌ Conexão perdida com o servidor. ' +
            '<button class="btn btn-back" onclick="location.reload()" style="margin-top:12px;">' +
            '<i class="fas fa-redo"></i> Tentar novamente</button>';
    }
};
```

**Modificar** o handler de `case 'error'` (linha ~1035-1037):

```js
// ANTES
case 'error':
    document.getElementById('progressStatus').textContent = `❌ ${msg.message}`;
    break;
```

```js
// DEPOIS
case 'error':
    document.getElementById('progressStatus').innerHTML =
        `❌ ${msg.message}<br>` +
        `<button class="btn btn-back" onclick="location.reload()" style="margin-top:12px;">` +
        `<i class="fas fa-redo"></i> Tentar novamente</button>`;
    break;
```

### ✅ Checkpoint Fase 1

```bash
python server.py
```
- Abrir `http://localhost:8000`
- Ir até a tela de progresso (visualmente) e confirmar que os 9 steps aparecem com nomes corretos
- Fechar o servidor enquanto estiver gerando → verificar mensagem "Conexão perdida" com botão

---

## Fase 2: Validações

### 2.1 — Validação de domínio obrigatório

**Arquivo:** `frontend/index.html`

**Substituir** a função `validateStep0()` (linhas ~803-809):

```js
// ANTES
function validateStep0() {
    const nome = document.getElementById('empresa_nome').value.trim();
    const categoria = document.getElementById('categoria').value.trim();
    if (!nome) { alert('Preencha o nome da empresa'); return false; }
    if (!categoria) { alert('Preencha o nicho/categoria'); return false; }
    return true;
}
```

```js
// DEPOIS
function validateStep0() {
    const nome = document.getElementById('empresa_nome').value.trim();
    const dominio = document.getElementById('dominio').value.trim();
    const categoria = document.getElementById('categoria').value.trim();
    const telefone = document.getElementById('telefone').value.trim();
    if (!nome) { alert('Preencha o nome da empresa'); return false; }
    if (!dominio) { alert('Preencha o domínio do site'); return false; }
    if (!categoria) { alert('Preencha o nicho/categoria'); return false; }
    if (!telefone) { alert('Preencha o WhatsApp'); return false; }
    return true;
}
```

### 2.2 — Validação de keywords (Step 1)

**Arquivo:** `frontend/index.html`

**Adicionar** após `validateStep0()`:

```js
function validateStep1() {
    const keywords = getAllKeywords();
    if (keywords.length === 0) {
        alert('Adicione pelo menos uma palavra-chave (CSV ou manual)');
        return false;
    }
    return true;
}
```

### 2.3 — Validação de locais (Step 2)

**Adicionar** após `validateStep1()`:

```js
function validateStep2() {
    const locais = document.getElementById('locais').value
        .split('\n').map(l => l.trim()).filter(l => l);
    if (locais.length === 0) {
        alert('Adicione pelo menos uma cidade ou bairro');
        return false;
    }
    return true;
}
```

### 2.4 — Integrar validações no `nextStep()`

**Substituir** o bloco de `nextStep()` (linhas ~787-795):

```js
// ANTES
function nextStep() {
    if (currentStep === 0 && !validateStep0()) return;
    if (currentStep === 1) updateKeywordsPreview();
    if (currentStep === 2) updatePagesEstimate();
    if (currentStep === 3) updateReview();

    currentStep = Math.min(currentStep + 1, totalSteps - 1);
    showPanel(currentStep);
}
```

```js
// DEPOIS
function nextStep() {
    if (currentStep === 0 && !validateStep0()) return;
    if (currentStep === 1) {
        updateKeywordsPreview();
        if (!validateStep1()) return;
    }
    if (currentStep === 2) {
        updatePagesEstimate();
        if (!validateStep2()) return;
    }
    if (currentStep === 3) updateReview();

    currentStep = Math.min(currentStep + 1, totalSteps - 1);
    showPanel(currentStep);
}
```

### ✅ Checkpoint Fase 2

- Abrir `http://localhost:8000`
- Tentar avançar Step 0 sem domínio → **deve bloquear**
- Tentar avançar Step 0 sem telefone → **deve bloquear**
- Tentar avançar Step 1 sem keywords → **deve bloquear**
- Tentar avançar Step 2 sem locais → **deve bloquear**
- Preenchendo tudo, deve avançar normalmente

---

## Fase 3: Campos de Leads

### 3.1 — Adicionar UI para `worker_url` e `client_token`

**Arquivo:** `frontend/index.html`

**Adicionar** no Step 3 (Identidade Visual), **após** o campo do Google Maps (após linha ~672), antes do `btn-row`:

```html
<div style="margin-top:32px; padding-top:24px; border-top:1px solid #1e293b;">
    <h3 style="font-size:1.1rem; font-weight:600; margin-bottom:6px;">Captura de Leads</h3>
    <p style="font-size:0.85rem; color:#64748b; margin-bottom:20px;">Opcional — conecte ao Cloudflare Worker para rastrear leads do WhatsApp.</p>

    <div class="field">
        <label>URL do Cloudflare Worker</label>
        <input type="text" id="worker_url" placeholder="https://leads.meusite.workers.dev">
        <p class="field-hint">Endpoint do Worker que recebe os dados do formulário</p>
    </div>
    <div class="field">
        <label>Token do Cliente</label>
        <input type="text" id="client_token" placeholder="token-unico-do-cliente">
        <p class="field-hint">Identificador único para filtrar leads no Dashboard</p>
    </div>
</div>
```

### 3.2 — Incluir no payload de `startGeneration()`

**Arquivo:** `frontend/index.html`

**No objeto `data` dentro de `startGeneration()`** (linhas ~920-935), adicionar após `max_workers: 30`:

```js
worker_url: document.getElementById('worker_url').value.trim(),
client_token: document.getElementById('client_token').value.trim(),
```

### 3.3 — Incluir na tela de Review

**Arquivo:** `frontend/index.html`

**Adicionar** no `updateReview()` (após linha ~911, antes do `}`), o seguinte:

```js
// Leads
const workerUrl = document.getElementById('worker_url').value.trim();
if (workerUrl) {
    document.getElementById('r_cost').insertAdjacentHTML('afterend',
        '<div style="font-size:0.85rem; color:#a5b4fc; margin-top:8px;">🔗 Captura de leads ativada</div>'
    );
}
```

### ✅ Checkpoint Fase 3

- Abrir `http://localhost:8000`
- Navegar até Step 3 → campos de leads devem aparecer com label "Captura de Leads"
- Preencher worker_url e client_token → avançar para Review → deve mostrar "Captura de leads ativada"
- Abrir console/DevTools Network → ao gerar, verificar que o JSON do WebSocket inclui `worker_url` e `client_token`

---

## Fase 4: Testes Automatizados

### 4.1 — Criar `tests/test_server.py`

**Arquivo:** `tests/test_server.py` (NOVO)

```python
"""
Testes do server.py — _build_config() e endpoint upload-csv.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app, _build_config


class TestBuildConfig:
    """Testes para a função _build_config()."""

    def test_basic_fields(self):
        data = {
            'empresa_nome': 'PetVida',
            'dominio': 'petvida.com.br',
            'categoria': 'Pet Shop',
            'telefone': '5541999998888',
            'horario': 'Seg a Sex, 8h às 18h',
            'endereco': 'Rua das Flores, 123',
            'servicos': 'Banho e Tosa\nConsulta Veterinária',
            'cor_marca': '#22c55e',
            'google_maps': '',
            'keywords_manual': 'Pet Shop\nBanho e Tosa',
            'locations': 'Curitiba\nSão José dos Pinhais',
        }
        config = _build_config(data)

        assert config['empresa']['nome'] == 'PetVida'
        assert config['empresa']['dominio'] == 'petvida.com.br'
        assert config['empresa']['categoria'] == 'Pet Shop'
        assert config['empresa']['telefone_whatsapp'] == '5541999998888'
        assert config['empresa']['cor_marca'] == '#22c55e'
        assert len(config['empresa']['servicos_manuais']) == 2
        assert config['seo']['palavras_chave'] == ['Pet Shop', 'Banho e Tosa']
        assert config['seo']['locais'] == ['Curitiba', 'São José dos Pinhais']

    def test_default_values(self):
        data = {}
        config = _build_config(data)

        assert config['empresa']['nome'] == ''
        assert config['empresa']['cor_marca'] == '#2563EB'
        assert config['api']['model'] == 'deepseek/deepseek-v3.2'
        assert config['api']['max_workers'] == 30
        assert config['api']['max_retries'] == 3

    def test_google_maps_iframe_extraction(self):
        data = {
            'google_maps': '<iframe src="https://maps.google.com/embed?pb=abc123" width="600"></iframe>',
        }
        config = _build_config(data)
        assert config['empresa']['google_maps_embed'] == 'https://maps.google.com/embed?pb=abc123'

    def test_google_maps_plain_url(self):
        data = {
            'google_maps': 'https://maps.google.com/embed?pb=abc123',
        }
        config = _build_config(data)
        assert config['empresa']['google_maps_embed'] == 'https://maps.google.com/embed?pb=abc123'

    def test_leads_fields(self):
        data = {
            'worker_url': 'https://leads.example.workers.dev',
            'client_token': 'token-abc-123',
        }
        config = _build_config(data)
        assert config['leads']['worker_url'] == 'https://leads.example.workers.dev'
        assert config['leads']['client_token'] == 'token-abc-123'

    def test_empty_keywords_and_locations(self):
        data = {
            'keywords_manual': '',
            'locations': '',
        }
        config = _build_config(data)
        assert config['seo']['palavras_chave'] == []
        assert config['seo']['locais'] == []

    def test_keywords_dedup_with_whitespace(self):
        data = {
            'keywords_manual': 'Pet Shop\n  Banho e Tosa  \n\nPet Shop\n',
            'locations': 'Curitiba\n\n  \nSão José\n',
        }
        config = _build_config(data)
        # Manual keywords don't dedup in _build_config (dedup is in frontend)
        assert 'Pet Shop' in config['seo']['palavras_chave']
        assert 'Banho e Tosa' in config['seo']['palavras_chave']
        assert 'Curitiba' in config['seo']['locais']
        assert 'São José' in config['seo']['locais']
        # Empty lines should be filtered
        assert '' not in config['seo']['locais']
        assert '' not in config['seo']['palavras_chave']


class TestUploadCSV:
    """Testes do endpoint /api/upload-csv."""

    def test_upload_valid_csv(self, tmp_path):
        """Upload de CSV simples com keywords."""
        csv_content = "Keyword\nPet Shop Curitiba\nBanho e Tosa\nConsulta Veterinária\n"
        client = TestClient(app)

        resp = client.post(
            "/api/upload-csv",
            files={"file": ("keywords.csv", csv_content.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['count'] >= 1
        assert isinstance(data['keywords'], list)

    def test_upload_empty_file(self):
        """Upload de arquivo vazio."""
        client = TestClient(app)
        resp = client.post(
            "/api/upload-csv",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['count'] == 0


class TestDownloadEndpoint:
    """Testes do endpoint /api/download."""

    def test_path_traversal_blocked(self):
        """Path traversal deve retornar 400."""
        client = TestClient(app)
        resp = client.get("/api/download/../../etc/passwd")
        assert resp.status_code == 400

    def test_nonexistent_file(self):
        """Arquivo inexistente deve retornar 404."""
        client = TestClient(app)
        resp = client.get("/api/download/naoexiste.com.br")
        assert resp.status_code == 404
```

### ✅ Checkpoint Fase 4

```bash
pytest tests/test_server.py -v
```
Todos os testes devem passar. Depois:
```bash
pytest tests/ --cov=core --cov-fail-under=75
```
Coverage deve continuar ≥ 75%.

---

## Fase 5: Teste Manual E2E

### 5.1 — Preparação

```bash
python server.py
```
Abrir `http://localhost:8000` no browser.

### 5.2 — Dados de teste

Preencher com (ou dados similares reais):

| Campo | Valor |
|---|---|
| Nome da Empresa | PetVida |
| Domínio | petvida.com.br |
| Categoria | Pet Shop |
| WhatsApp | 5541999998888 |
| Horário | Segunda a Sábado, 8h às 18h |
| Serviços | Banho e Tosa\nConsulta Veterinária\nVacinação |
| Keywords (manual) | Pet Shop\nBanho e Tosa\nClínica Veterinária |
| Locais | Curitiba\nSão José dos Pinhais |
| Cor | #22c55e |

### 5.3 — Checklist de verificação

- [x] Step 0: Todos os campos preenchidos, avançou sem erro
- [x] Step 1: Keywords aparecem como tags no preview
- [x] Step 2: Estimativa mostra "3 keywords × 2 locais = 6 páginas"
- [x] Step 3: Cor muda no picker, campos de leads visíveis
- [x] Step 4 (Review): Dados corretos, custo estimado aparece
- [x] Progresso: 9 steps aparecem na lista
- [x] Progresso: Barra circular avança conforme steps
- [x] Progresso: Contagem x/6 páginas atualiza em tempo real
- [x] Completo: Estatísticas aparecem (páginas, palavras, custo, tempo)
- [x] Download: ZIP baixa corretamente
- [x] ZIP: `index.html` abre no browser com design premium
- [x] ZIP: Subpáginas existem (6 arquivos .html)
- [x] ZIP: `sitemap.xml` existe
- [x] ZIP: `robots.txt` existe

---

## Ordem de Execução

```
Fase 1 → Checkpoint 1 → Fase 2 → Checkpoint 2 → Fase 3 → Checkpoint 3 → Fase 4 → Checkpoint 4 → Fase 5
```

**Regra:** Não avançar para a próxima fase sem o checkpoint da fase anterior passar.
