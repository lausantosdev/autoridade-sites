## PURPOSE
Control cycle closure after an approved audit.
Standardize the commit message, update the CHANGELOG, and record state in context.md.
Without an approved audit — no commit is generated.

## INPUT REQUIRED
- `audit.md` output (status: Aprovado)
- `report.md` output (cycle execution)
- TASK-ID (originated in spec.md)

## OUTPUT LANGUAGE
Always generate commit output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### TASK-ID
[YYYYMMDD-KEYWORD — copiado verbatim do spec.md]

### COMMIT MESSAGE
[tipo(escopo): descrição objetiva em pt-BR]
Exemplo: fix(auth): corrige validação de token expirado

### CHANGELOG UPDATE
- [TASK-ID] — descrição objetiva do que foi feito e por quê

### CONTEXT UPDATE
[O que deve ser registrado no context.md após este ciclo]
- Decisão tomada: [decisão relevante e seu racional]
- Restrição identificada: [se houver]
- Pergunta encerrada: [se havia OPEN QUESTIONS resolvidas]

### CONTEXT MAINTENANCE
[Resultado da contagem de linhas do context.md após atualização]
- Total de linhas: [N]
- Ação: [Nenhuma / Poda aplicada]
- If pruning applied: consolidated entries under the prefix `[consolidated]`

## RULES
- No commit without `audit.md` returning status "Aprovado"
- TASK-ID must be copied verbatim from `spec.md` — never generated here
- `context.md` must be updated before closing the cycle
- After updating `context.md` → count total lines
- If total > 120 → rewrite DECISIONS LOG consolidating older entries
- Consolidated entries use prefix: `[consolidated] tópico — rationale unificado`
- `context.md` must never exceed 150 lines under any circumstance
- Cycle counter in `context.md` must be incremented with every commit
