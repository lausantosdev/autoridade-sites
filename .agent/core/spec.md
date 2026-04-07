## PURPOSE
Define the "why" and "what" before the agent defines the "how".
Mandatory step zero — without an approved spec, plan.md is not generated.
Responsible for generating the TASK-ID that cascades through the entire cycle.

## OUTPUT LANGUAGE
Always generate spec output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### TASK-ID
[YYYYMMDD-KEYWORD — uma palavra extraída da User Story que descreva a essência da task]
Exemplo: 20260407-LOGIN-FIX

### USER STORY
[Descrição do problema ou necessidade — perspectiva do operador humano]

### ACCEPTANCE CRITERIA
- [Condição objetiva e verificável que define "feito"]
- [Cada critério deve ser testável ou diff-verificável]

### OUT OF SCOPE
- [O que explicitamente não será feito neste ciclo]
- If none: "Nenhum"

### OPEN QUESTIONS
- [Ambiguidades ou dependências não resolvidas que bloqueiam o ciclo]
- If none: "Nenhum"

## RULES
- `spec.md` must exist and be approved before `plan.md` is generated
- The TASK-ID generated here is the single source of truth — no other file generates TASK-ID
- TASK-ID travels in cascade: `spec → plan → exec → report → audit → fix → commit`
- Mandatory header in all cycle files: `TASK-ID: YYYYMMDD-KEYWORD`
- If the User Story is ambiguous or incomplete → output `[UNCERTAIN: spec]` and stop
- If OPEN QUESTIONS contain blocking items → output `[UNCERTAIN: spec]` and stop
- Do not infer scope from the User Story — whatever is not explicit is out of scope
