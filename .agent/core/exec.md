# .agent/exec.md

## PURPOSE
Control execution behavior after the plan is approved.
No deviation from the plan is allowed during execution.
If a deviation is required → stop, emit the appropriate tag, and wait.

## OUTPUT LANGUAGE
Always generate execution output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### EXECUTION STATUS
[Em andamento / Concluído / Bloqueado]

### STEPS EXECUTED
1. [Ação executada — o quê, onde, resultado]
2. [Ação executada — o quê, onde, resultado]
...

### FILES MODIFIED
- path/to/file.ext — descrição da mudança

### BLOCKERS
- [O que impediu ou pode impedir a conclusão]
- Se nenhum: "Nenhum"

### NEXT
[Próximo passo: gerar report.md / aguardar instrução / emitir tag]

## RULES
- Execute ONLY the steps defined in plan.md — no additions, no shortcuts
- If a step is ambiguous → output `[UNCERTAIN: step N]` and stop
- If a step requires touching an out-of-scope file → output `[UNCERTAIN: scope]` and stop
- If execution fails or produces unexpected behavior → output `[ESCALATE]` and stop
- If a deviation from the plan is required for any reason → output `[UNCERTAIN: deviation]` and stop
- Do NOT proceed to the next step if the current step produced an error
- Do NOT commit during execution — commit happens only after a passing audit
- After execution is complete → trigger report.md
