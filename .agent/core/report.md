# .agent/report.md

## PURPOSE
Document what was executed and its outcome.
The report is the handoff artifact between execution and audit.
It must be objective, complete, and diff-verifiable.

## OUTPUT LANGUAGE
Always generate report output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### TASK
[Repetir a task exata do plan.md — sem parafrasear]

### STATUS
[Concluído / Concluído com ressalvas / Bloqueado]

### FILES MODIFIED
- path/to/file.ext — descrição objetiva da mudança

### SUMMARY
[O que foi feito, em linguagem direta. Sem justificativas, sem contexto extra.]

### DIFF SUMMARY
[Descrição do que o git diff deve mostrar — por arquivo]
- path/to/file.ext: [o que mudou]

### VALIDATION
[O resultado atende ao EXPECTED OUTCOME definido no plano?]
- Sim / Não / Parcialmente — motivo objetivo

### OPEN ISSUES
- [Qualquer comportamento inesperado, warning, ou ponto de atenção]
- Se nenhum: "Nenhum"

### NEXT
[Próximo passo: acionar audit.md / emitir tag / aguardar instrução]

## RULES
- TASK must be copied verbatim from plan.md — do not rephrase
- SUMMARY must describe what happened, not what was intended
- DIFF SUMMARY must be consistent with actual git diff — auditor will verify
- If VALIDATION is "Não" or "Parcialmente" → output `[UNCERTAIN: validation]`
- If any OPEN ISSUES are critical → output `[ESCALATE]`
- Do NOT omit files from FILES MODIFIED — partial reporting breaks the audit
- After report is complete → trigger audit.md
