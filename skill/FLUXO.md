# Workflow — Gemini + Sonnet

Fluxo de 6 fases com handoff estruturado entre agentes.

---

## Visão geral

```
[Gemini] /explore-problem
         ↓
[Sonnet] /analyze-proposal
         ↓
[Sonnet] /create-spec
         ↓
[Gemini] /execute-spec
         ↓
[Sonnet] /audit-execution
         ↓
[Gemini] /commit-push
```

---

## Fase 1 — Gemini: `/explore-problem`

**Onde:** Gemini CLI ou agente Gemini

```
/explore-problem

PROBLEMA:
[descrição livre do problema ou bug]
```

Mapeia o problema sem propor solução. Lê o código, traça o fluxo, formula hipóteses.

**Output:** análise estruturada com arquivos envolvidos, causa raiz, comportamento atual vs. esperado.

---

## Fase 2 — Sonnet: `/analyze-proposal`

**Onde:** Sonnet no antigravity (nova sessão)

```
/analyze-proposal

PROBLEMA:
[mesma descrição da fase 1]

PROPOSTA DO GEMINI:
[cole o output completo da fase 1]
```

Revisão adversarial. Encontra o que o Gemini não viu.

**Output:** riscos críticos, gaps, edge cases, veredicto (Aprovado / Requer Correção / Rejeitar).

---

## Fase 3 — Sonnet: `/create-spec`

**Onde:** mesmo chat do Sonnet (sem trocar de janela)

```
/create-spec

PROBLEMA:
[mesma descrição]

ANÁLISE CRÍTICA:
[cole o output da fase 2]
```

Cria a Spec executável para o Gemini. Escopo fechado, mudanças por arquivo, critérios de aceitação.

**Output:** Spec técnica completa. Esse documento é o contrato entre Sonnet e Gemini.

---

## Fase 4 — Gemini: `/execute-spec`

**Onde:** Gemini CLI ou agente Gemini

```
/execute-spec

SPEC:
[cole o output completo da fase 3]
```

Executa exatamente o que está na Spec. Não improvisa, não expande escopo, registra log de decisões.

**Output:** log de execução com arquivos modificados, decisões tomadas, desvios e autoavaliação dos critérios.

---

## Fase 5 — Sonnet: `/audit-execution`

**Onde:** Sonnet no antigravity (mesmo chat ou novo)

```
/audit-execution

SPEC ORIGINAL:
[cole a Spec da fase 3]

MUDANÇAS EXECUTADAS:
[cole o log da fase 4 ou o output de: git diff HEAD~1]
```

Audita sistematicamente a execução contra a Spec.

**Output:** tabela de critérios (OK/Parcial/Falhou), desvios críticos vs. menores, lista de correções priorizadas.

- Se **APROVADO** → segue para fase 6
- Se **REQUER CORREÇÃO** → volta para fase 4 com as correções listadas

---

## Fase 6 — Gemini: `/commit-push`

**Onde:** Gemini CLI ou agente Gemini

```
/commit-push

LOG DE EXECUÇÃO:
[cole o log da fase 4]

RESULTADO DA AUDITORIA:
[cole o output da fase 5]
```

Só executar após auditoria **APROVADO** ou **APROVADO COM RESSALVAS**.

Gera mensagem de commit derivada da Spec, faz `git add` explícito (nunca `git add .`), commit e push.

---

## Ciclo de correção (quando necessário)

Se o audit-execution retornar **REQUER CORREÇÃO**:

```
[Sonnet] /audit-execution → lista de correções
         ↓
[Gemini] /execute-spec → re-executa com foco nas correções
         ↓
[Sonnet] /audit-execution → nova auditoria
         ↓ (se aprovado)
[Gemini] /commit-push
```

---

## Onde cada skill vive

| Skill | Arquivo | Agente |
|---|---|---|
| `/explore-problem` | `explore-problem.md` | Gemini |
| `/analyze-proposal` | `analyze-proposal.md` | Sonnet |
| `/create-spec` | `create-spec.md` | Sonnet |
| `/execute-spec` | `execute-spec.md` | Gemini |
| `/audit-execution` | `audit-execution.md` | Sonnet |
| `/commit-push` | `commit-push.md` | Gemini |
