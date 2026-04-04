# SPEC — Sessão 1 (04/04/2026): Bugs Visuais e Coverage Recovery

> **Atividade:** Bugs Visuais + Estabilização Técnica
> **Plano associado:** `PLAN_BUGS_VISUAIS_04_04_2026.md`
> **Pré-requisito:** `.env` com `OPENROUTER_API_KEY` e `GEMINI_API_KEY` válidas

---

## Sumário de Fases

- [x] Fase 1: Recovery de cobertura de testes (`test_color_utils.py`)
- [x] Fase 2: Fix de prompt — B-04 (`hero_subtitle` longo)
- [x] Fase 3: Validação visual no browser (B-01, B-02, B-03, B-04 resolvidos. B-05 transferido para Sessão 2)
- [x] Fase 4: Teste E2E final do Wizard

---

## Fase 1 — Recovery de Coverage

### Contexto

A adição de `core/color_utils.py` (137 linhas) sem testes correspondentes derrubou a cobertura de 79% → 73%. O CI está vermelho. Todas as funções são matemática pura — sem IA, sem I/O, sem mocks necessários.

### Módulo alvo

`tests/test_color_utils.py` [NOVO]

### Casos de teste obrigatórios

**`TestHexToRgb`**
- `test_hex6`: `#FF8800` → `(255, 136, 0)` ✓
- `test_hex3`: `#F80` → `(255, 136, 0)` (shorthand expandido) ✓
- `test_lowercase`: `#ff8800` deve funcionar igual ao uppercase ✓
- `test_black`: `#000000` → `(0, 0, 0)` ✓
- `test_white`: `#FFFFFF` → `(255, 255, 255)` ✓

**`TestRgbToHsl`**
- `test_black`: `(0,0,0)` → h=0, s=0, l=0 ✓
- `test_white`: `(255,255,255)` → h=0, s=0, l=100 ✓
- `test_red`: `(255,0,0)` → h=0, s=100, l=50 ✓
- `test_green`: `(0,255,0)` → h=120, s=100, l=50 ✓
- `test_blue`: `(0,0,255)` → h=240, s=100, l=50 ✓

**`TestHslToHex`** (roundtrip)
- `test_roundtrip_red`: hex `#FF0000` → rgb → hsl → hex deve voltar para `#FF0000` ✓
- `test_roundtrip_blue`: mesma lógica para `#0000FF` ✓

**`TestContrastRatio`**
- `test_identical_colors`: duas cores iguais → razão = 1.0 ✓
- `test_black_white`: `#000000` vs `#FFFFFF` → razão ≈ 21.0 ✓
- `test_wcag_aa_threshold`: resultado > 4.5 deve ser True para preto sobre branco ✓

**`TestEnsureTextContrast`**
- `test_light_mode_yellow_fails`: amarelo `#FACC15` no tema light tem contraste insuficiente com branco → função deve retornar cor mais escura ✓
- `test_dark_mode_dark_color_fails`: azul-escuro `#1E3A5F` no tema dark tem contraste insuficiente com `#0b0d11` → função deve retornar cor mais clara ✓
- `test_already_compliant_dark`: preto `#000000` no tema light já tem contraste > 4.5 → função deve retornar a mesma cor sem alterar ✓
- `test_already_compliant_white`: branco `#FFFFFF` no tema dark já tem contraste > 4.5 → função deve retornar a mesma cor sem alterar ✓
- `test_output_is_hex_string`: resultado sempre começa com `#` ✓

### Checkpoint Fase 1

```bash
pytest tests/test_color_utils.py -v
```
> ✅ Todos os testes devem passar.

```bash
pytest tests/ --cov=core --cov-fail-under=75
```
> ✅ Coverage total ≥ 75%. Não avançar se falhar.

---

## Fase 2 — Fix de Prompt B-04 (`hero_subtitle` longo)

### Contexto

**Root cause confirmado:** o prompt de `site_data_builder.py` não impõe limite de palavras para `hero_subtitle`. Em mobile, o campo aparece com 5 linhas quebrando o layout.

**B-03 (Subpágina sem hero image) — RE-ANÁLISE:**
> O `page.html` linha 60 já contém `style="background-image: url('images/hero.jpg');"` e o `generate.py` copia `hero-image.jpg` → `images/hero.jpg`. Portanto B-03 é provavelmente um **bug de CSS** (o background é sobrescrito) — não de código Python. A Fase 3 (validação visual) irá confirmar ou refutar.

### Arquivo alvo: `core/site_data_builder.py`

Localizar a função que monta o prompt da home (a que contém `hero_subtitle`).

Adicionar instrução explícita no prompt, junto ao campo `hero_subtitle`:
- Máximo de **15 palavras**
- Uma frase direta, sem vírgulas encadeadas
- **ERRADO:** "Oferecemos atendimento completo com toda a equipe especializada no cuidado do seu animal, com carinho e profissionalismo desde 2010"
- **CERTO:** "Atendimento veterinário especializado com carinho e profissionalismo."

### Checkpoint Fase 2

```bash
python -c "
from core.config_loader import load_config
from core.openrouter_client import OpenRouterClient
from core.site_data_builder import build_site_data, resolve_theme_mode

config = load_config('config-test.yaml')
client = OpenRouterClient(model=config['api']['model'], max_retries=1)
resolve_theme_mode(config, client)
data = build_site_data(config, client)
subtitle = data.get('hero_subtitle', '')
words = len(subtitle.split())
print(f'hero_subtitle ({words} palavras): {subtitle}')
assert words <= 20, f'FALHOU: {words} palavras'
print('OK - dentro do limite')
"
```
> ✅ Saída deve mostrar `hero_subtitle` com ≤ 20 palavras. Não avançar se falhar.

---

## Fase 3 — Validação Visual no Browser (B-01 a B-05)

### Contexto

Os patches de CSS para B-01 e B-05 foram injetados no `template-dist/index.html` mas **nunca verificados visualmente**. B-03 precisa ser avaliado no browser. B-02 precisa ser confirmado investigando o bundle JS compilado.

### 3.1 — Gerar site de teste com cor problemática

Criar `config-visual-test.yaml` (cópia de `config-test.yaml`) com:
- `cor_marca: "#F59E0B"` (amarelo — o pior caso para B-02 no tema light)
- `locais: ["São Paulo", "Campinas", "Guarulhos"]` (3 locais)
- `palavras_chave: ["Veterinário", "Banho e Tosa"]` (2 keywords → 6 subpáginas)
- `empresa.servicos_manuais: ["Banho e Tosa", "Consulta Veterinária", "Vacinação", "Cirurgia", "Dentição"]` (5 serviços → força o cenário do ghost card do B-01)

```bash
python generate.py --config config-visual-test.yaml
```

> ⚠️ Se já existir `output/petvida.test/`, deletar antes para forçar regeneração completa.

### 3.2 — Servir localmente

```bash
cd output/petvida.test
python -m http.server 8080
```

### 3.3 — Checklist de validação visual (usar browser_subagent)

Abrir `http://localhost:8080` e verificar:

**Home Page:**
- [x] **B-01:** Grid de serviços com 5 cards — confirmar que **NÃO aparece slot cinza/vazio** na última linha
- [x] **B-02:** Badge/textos na cor `#F59E0B` (amarelo) no tema light — confirmar se estão **legíveis** (texto escuro sobre fundo claro). Se ilegíveis, registrar o valor exato da cor exibida pelo DevTools
- [ ] **B-05:** Medir visualmente o espaço entre topo do hero e o badge — **[⚠️ TRANSFERIDO PARA SESSÃO 2]**

**Subpágina** (abrir qualquer `veterinario-sao-paulo.html` ou equivalente):
- [ ] **B-03:** Hero da subpágina tem `hero-image.jpg` como background visível (não apenas cor sólida)
- [ ] **B-04:** `hero_subtitle` ocupa **no máximo 2 linhas** no mobile (emular via DevTools)

### 3.4 — Ação corretiva se B-02 ainda falhar

Verificar no DevTools qual propriedade de cor o React está lendo:
- Se `colorText` estiver sendo usado → o problema é no valor gerado pelo `ensure_text_contrast`. Corrigir a lógica de `color_utils.py`.
- Se `color` (bruto) estiver sendo usado → o React ignora o `colorText`. Solução: adicionar CSS override no bloco `<style>` do `template-dist/index.html` forçando a cor ajustada nos elementos críticos de texto.

### 3.5 — Ação corretiva se B-03 ainda falhar

Se a imagem de hero não aparecer nas subpáginas:
- Inspecionar no DevTools se o `background-image` da `section.hero` está sendo sobrescrito por outro CSS
- Se sim, adicionar `!important` no CSS inline da `section.hero` do `page.html`

### Checkpoint Fase 3

> ✅ Todos os 5 itens do checklist marcados como OK.
> Se qualquer correção adicional foi necessária, rodar novamente:
> ```bash
> pytest tests/ --cov=core --cov-fail-under=75
> ```

---

## Fase 4 — Teste E2E Final do Wizard

### Contexto

Fase 5 da `SPEC_SESSAO1_03_04_2026.md` (wizard-e2e), pendente desde a última sessão. Agora que os bugs visuais estão corrigidos, o site gerado pelo Wizard terá qualidade premium.

### 4.1 — Iniciar o servidor

```bash
python server.py
```

### 4.2 — Dados para preencher no Wizard

| Campo | Valor |
|---|---|
| Nome da Empresa | PetVida Clínica |
| Domínio | petvida-clinica.com.br |
| Categoria | Clínica Veterinária |
| WhatsApp | 5511999991234 |
| Horário | Segunda a Sábado, 8h às 20h |
| Serviços (linha por linha) | Banho e Tosa \| Consulta Veterinária \| Vacinação \| Cirurgia \| Dentição |
| Keywords (manual) | Veterinário \| Banho e Tosa \| Clínica Veterinária |
| Locais | São Paulo \| Campinas \| Guarulhos |
| Cor | #22c55e |

### 4.3 — Checklist do Wizard (browser_subagent)

**Navegação pelo Wizard:**
- [ ] Step 0: Todos os campos preenchidos, avança sem alerta de erro
- [ ] Step 1: Keywords aparecem como tags no preview
- [ ] Step 2: Estimativa exibe "3 keywords × 3 locais = 9 páginas"
- [ ] Step 3: Cor muda no picker; campos "Captura de Leads" visíveis
- [ ] Step 4 (Review): Todos os dados corretos, custo estimado aparece

**Progresso de geração:**
- [ ] 9 steps aparecem na lista lateral com nomes corretos
- [ ] Barra circular avança progressivamente
- [ ] Contagem "x/9 páginas" atualiza em tempo real

**Resultado e download:**
- [ ] Tela de conclusão exibe estatísticas (páginas, palavras, custo, tempo)
- [ ] Botão de download aparece; ZIP baixa corretamente

**Inspeção do ZIP descompactado:**
- [ ] `index.html` abre no browser com design premium
- [ ] 9 subpáginas `.html` existem
- [ ] `sitemap.xml` existe e lista todas as páginas
- [ ] `robots.txt` existe
- [ ] Hero da home tem imagem de fundo visível
- [ ] Hero de subpágina tem imagem de fundo visível (B-03)
- [ ] Grid de serviços sem ghost card (B-01)
- [ ] Cor da marca legível no tema gerado (B-02)

### Checkpoint Fase 4

> ✅ Todos os itens do checklist marcados como OK.
> Este checkpoint finaliza a sessão 4 e a atividade `wizard-e2e` SPEC_SESSAO1_03_04_2026.md.

---

## Ordem de Execução

```
Fase 1 → Checkpoint Coverage → Fase 2 → Checkpoint Prompt → Fase 3 → Checklist Visual → Fase 4 → Checklist E2E
```

**Regra absoluta:** não avançar para a próxima fase sem o checkpoint anterior ter passado. Se um checkpoint falhar, corrigir e re-testar antes de continuar.
