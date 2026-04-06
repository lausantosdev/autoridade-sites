# .agent/plan.md

## PURPOSE
Define the execution contract before any code is written.
A plan is mandatory. No execution without a plan.

## OUTPUT LANGUAGE
Always generate plan output in Brazilian Portuguese (pt-BR).
This applies only to the body content under each header.
Headers (### TASK, ### SCOPE, ### STEPS, etc.) must remain in English — they are structural anchors.
File paths and code identifiers remain in their original form.
Tags ([ESCALATE], [UNCERTAIN]) remain in English — they are machine-readable markers.

## FORMAT

### TASK
[Uma frase descrevendo o objetivo]

### SCOPE
Files in scope:
- path/to/file.ext — motivo

Files out of scope:
- path/to/file.ext — motivo (se relevante)

### STEPS
1. [Ação atômica — o quê, onde, por quê]
2. [Ação atômica — o quê, onde, por quê]
...

### EXPECTED OUTCOME
[O que o sistema deve fazer/ser após a execução — testável se possível]

### RISKS
- [Qualquer coisa que possa dar errado ou exigir escalação]

### ESCALATION CONDITIONS
- [Condições que bloqueariam a execução antes de começar]
- Se qualquer risco for crítico (auth, DB, lógica core) → emitir `[ESCALATE]` antes de prosseguir

## RULES
- Steps must be atomic — one action per step
- Steps must reference specific files, not directories
- Scope must be declared before execution begins
- If scope is unclear → output `[UNCERTAIN: scope]` and stop
- Do NOT begin execution if the plan has unresolved `[UNCERTAIN]` items
- Plan must be approved (or self-approved if autonomous) before exec.md is triggered
