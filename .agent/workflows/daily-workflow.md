---
description: Pipeline de trabalho diário do projeto SiteGen
---

# Pipeline de Trabalho Diário — SiteGen

Siga este fluxo em **toda sessão de trabalho**, sem exceção.
Este workflow tem dois atos: **Report de Status** (leitura) e **Próximo Passo** (decisão).
Nunca execute código ou modifique arquivos durante o Ato 1.

---

## 🔍 ATO 1 — REPORT DE STATUS (somente leitura)

Execute os passos abaixo silenciosamente (sem comentários intermediários) e entregue o report completo de uma vez.

### Passo 1: Carregar contexto

Leia os seguintes arquivos nesta ordem:
1. `SESSIONS_LOG.md` — última entrada
2. `ROADMAP.md` — seções "Em Progresso" e "Backlog"
3. `docs/` — liste as pastas existentes e, para cada uma, verifique:
   - Se existe `PLAN_*.md` → leia o campo **Status** no final do arquivo
   - Se existe `SPEC_SESSAO*.md` → leia as checkboxes `- [ ]` / `- [x]` e calcule quantas fases estão concluídas vs. pendentes

### Passo 2: Montar e retornar o report

Retorne o seguinte report formatado, **antes de qualquer pergunta**:

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 STATUS DO PROJETO — SiteGen
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CONCLUÍDO (última sessão)
- [listar o que o SESSIONS_LOG marca como feito na última entrada]

🔄 EM ANDAMENTO
- Feature: [nome da atividade em docs/]
  - Plano: [existe / não existe]
  - Spec:  [X/N fases concluídas — ou "não gerada"]

📋 PRÓXIMAS ENTREGAS (conforme ROADMAP)
1. 🔴 [feature prioritária 1]
2. 🔴 [feature prioritária 2]
3. 🟡 [backlog técnico relevante]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ❓ ATO 2 — PRÓXIMO PASSO (decisão)

Com base no report acima, avalie **exatamente uma** das situações abaixo e faça a pergunta correspondente ao usuário:

### Situação A — Spec existe e tem fases pendentes
> A Spec `SPEC_SESSAO<N>_<DATA>.md` da atividade **[nome]** tem **X fases concluídas e Y pendentes**.
> Quer que eu execute a **próxima fase pendente** agora?

### Situação B — Plano existe mas Spec não foi gerada
> O Plano `PLAN_<ATIVIDADE>.md` existe e está aprovado, mas a Spec de execução ainda não foi criada.
> Quer que eu gere a `SPEC_SESSAO<N>_<DATA>.md` agora?

### Situação C — Nenhum Plano/Spec para a próxima feature prioritária
> A próxima entrega prioritária do ROADMAP é **[nome da feature]** e ainda não tem Plano de Implementação.
> Quer que eu faça o brainstorm técnico e apresente o Plano para sua aprovação?

### Situação D — Tudo concluído / nada em andamento
> Todas as atividades em `docs/` estão concluídas e não há nenhuma feature 🔴 em andamento no ROADMAP.
> Qual entrega você quer priorizar a seguir?

---

## ⚡ EXECUÇÃO (apenas após aprovação do usuário)

Somente após o usuário responder "sim" ou equivalente ao Ato 2:

7. **Execute fase a fase**, conforme a Spec aprovada
8. Ao final de cada fase, rode os testes definidos no checkpoint da Spec
   - Se um teste falhar: corrija antes de avançar
   - Não pule fases

---

## 🏁 FINAL DE SESSÃO (10 minutos)

// turbo
9. Rodar testes finais:
   ```bash
   python -m pytest tests/ --cov=core --cov-fail-under=75
   ```

10. Atualizar `SESSIONS_LOG.md`:
    - Marcar o que foi concluído com ✅
    - Listar itens para `🔜 Próxima Sessão`

11. Atualizar `ROADMAP.md`:
    - Mover itens de "Em Progresso" para "Entregue" se concluídos
    - Ajustar prioridades do backlog se necessário

12. Atualizar o status das fases no `PLAN_*.md` da atividade:
    - Marcar fases concluídas com `[x]`

// turbo
13. Commitar tudo:
    ```bash
    git add .
    git commit -m "sessão <N> <data>: <resumo do que foi feito>"
    ```

---

## 📁 Hierarquia de Documentos

```
CONTEXT.md              → Arquitetura     (O que é e como funciona — raramente muda)
ROADMAP.md              → Produto         (Para onde vai — atualiza por feature entregue)
SESSIONS_LOG.md         → Tático          (O que fizemos hoje — atualiza todo dia)
docs/<atividade>/       → Execução        (Plano + Specs de cada atividade)
```

**Regra:** `ROADMAP` → orienta o brainstorm → orienta o `PLAN` → orienta a `SPEC` → orienta o agente executor.

## 📂 Estrutura de `docs/`

```
docs/
└── <nome-atividade>/
    ├── PLAN_<ATIVIDADE>_<DATA>.md   ← plano de implementação (com Status: [] por fase)
    ├── SPEC_SESSAO1_<DATA>.md       ← spec da primeira sessão (com checkboxes por fase)
    └── SPEC_SESSAO2_<DATA>.md       ← spec da segunda sessão (se necessário)
```

**Convenção de nomes para specs:**
- `SPEC_SESSAO1_03_04_2026.md` — primeira sessão do dia
- `SPEC_SESSAO2_03_04_2026.md` — segunda sessão do mesmo dia
