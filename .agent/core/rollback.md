## PURPOSE
Define the rollback protocol when `[ESCALATE: manual]` is emitted.
Closes the terminal state — no new cycle may begin without executing this protocol first.
All automation stops. Human intervenes. This file governs what happens next.

## TRIGGER CONDITIONS
- `[ESCALATE: manual]` was emitted in any file of the current cycle
- Human explicitly requests rollback outside of an escalation flow

## INPUT REQUIRED
- `escalation.md` output (last available)
- `audit.md` output (last available)
- `fix.md` output (last available — if any)
- `context.md` current state
- Git log (current branch)

## OUTPUT LANGUAGE
Always generate rollback output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### ROLLBACK STATUS
[Concluído / Bloqueado]

### TRIGGER REASON
[Por que o rollback foi acionado — copiado verbatim do `[ESCALATE: manual]` que o originou]

### ROLLBACK STEPS
1. [Ação executada — o quê, onde, resultado]
2. [Ação executada — o quê, onde, resultado]
...

### CONTEXT UPDATE
[O que foi registrado no context.md — o que falhou e por quê]

### REOPEN PROTOCOL
[Condições necessárias para abrir uma nova task sobre este problema]
- Mandatory: new task must begin with a new `spec.md` and a new TASK-ID
- Describe what must be done differently in the new approach

## RULES
- Always use `git revert` — NEVER `git reset` on a shared branch
- `context.md` must be updated with what failed and why before any other action
- Every new task after a rollback must begin with a new `spec.md` and a new TASK-ID
- No new cycle may begin without `context.md` reflecting the rollback state
- If `git revert` fails or produces conflicts → output `[UNCERTAIN: revert]` and stop; human resolves manually
- Rollback does not close the underlying problem — it closes the failed cycle safely
- After rollback is complete → human reviews REOPEN PROTOCOL and decides next action
