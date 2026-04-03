---
description: Pipeline de trabalho diário do projeto SiteGen
---

# Pipeline de Trabalho Diário — SiteGen

Siga este fluxo em **toda sessão de trabalho**, sem exceção.

---

## Início de Sessão (5 minutos)

1. Leia a última entrada do `SESSIONS_LOG.md`
   - Identifique o que ficou para fazer (`🔜 Próxima Sessão`)

2. Leia o `ROADMAP.md`
   - Confirme qual é a **próxima entrega prioritária**
   - Features de produto 🔴 têm prioridade sobre polimento técnico 🟡

---

## Planejamento (antes de codar)

3. **Brainstorm — Plano de Implementação**
   Peça ao agente:
   > *"Leia CONTEXT.md, SESSIONS_LOG.md e ROADMAP.md. Com base na próxima entrega prioritária, faça o brainstorm técnico e apresente um Plano de Implementação para minha aprovação. Não execute nada ainda."*

   > ⚠️ **Uma atividade por plano.** Se a próxima entrega for grande (ex: Wizard + Leads + Dashboard), quebre em 3 planos separados. Comece pelo primeiro.

   O agente apresenta o plano com:
   - O que será feito e por quê
   - Arquivos afetados
   - Riscos e decisões em aberto (Open Questions)

4. **Revise e aprove o Plano**
   - Responda as Open Questions
   - Ajuste o escopo se necessário
   - Dê o "Ok" para avançar

5. **Spec de Execução**
   Após aprovação do plano, peça ao agente:
   > *"Plano aprovado. Crie a spec detalhada `SPEC_SESSAO<N>_<DD_MM_AAAA>.md` pronta para execução e salve junto com o plano em `docs/<nome-atividade>/`."*

   A spec deve conter:
   - Código exato a escrever
   - Modificações linha a linha
   - Checkpoints de testes entre fases

6. **Revise e aprove a Spec**
   - Confirme que a spec está completa e sem ambiguidade
   - Dê o "Ok" para executar

---

## Execução

7. Peça ao agente:
   > *"Spec aprovada. Execute fase a fase."*

8. O agente executa e roda testes ao final de cada fase
   - Se um teste falhar: corrige antes de avançar
   - Não pula fases

---

## Final de Sessão (10 minutos)

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

// turbo
12. Commitar tudo:
    ```bash
    git add .
    git commit -m "sessão <N> <data>: <resumo do que foi feito>"
    ```

---

## Hierarquia de Documentos

```
CONTEXT.md              → Arquitetura     (O que é e como funciona — raramente muda)
ROADMAP.md              → Produto         (Para onde vai — atualiza por feature entregue)
SESSIONS_LOG.md         → Tático          (O que fizemos hoje — atualiza todo dia)
docs/<atividade>/       → Execução        (Plano + Specs de cada atividade)
```

**Regra:** Cada documento orienta o próximo.
`ROADMAP` → orienta o brainstorm → orienta o `PLAN` → orienta a `SPEC` → orienta o agente executor.

## Estrutura de `docs/`

```
docs/
└── <nome-atividade>/          ← uma pasta por atividade do ROADMAP
    ├── PLAN_<ATIVIDADE>_<DATA>.md   ← plano de implementação aprovado
    ├── SPEC_SESSAO1_<DATA>.md       ← spec da primeira sessão
    └── SPEC_SESSAO2_<DATA>.md       ← spec da segunda sessão (se necessário)
```

**Exemplos de nomes de pasta:**
- `docs/wizard-e2e/`
- `docs/leads-integration/`
- `docs/dashboard/`
- `docs/polimento-tecnico/`

**Convenção de nomes para specs:**
- `SPEC_SESSAO1_03_04_2026.md` — primeira sessão do dia
- `SPEC_SESSAO2_03_04_2026.md` — segunda sessão do mesmo dia
