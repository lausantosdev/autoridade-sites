# .agent/fix.md

## PURPOSE
Apply minimal, targeted corrections identified by audit.md.
Fix only what is broken — nothing else.
No scope expansion. No refactoring. No improvements.

## INPUT REQUIRED
- audit.md output (issues + fix suggestions)
- report.md output (execution context)
- git diff (source of truth)

## OUTPUT LANGUAGE
Always generate fix output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### FIX STATUS
[Concluído / Concluído com ressalvas / Bloqueado]

### ISSUES ADDRESSED
- [Issue do audit.md — descrição copiada verbatim]
  - Correção aplicada: [o quê, onde, como]
  - Arquivo: path/to/file.ext

### FILES MODIFIED
- path/to/file.ext — descrição objetiva da mudança

### DIFF SUMMARY
[O que o git diff deve mostrar após o fix — por arquivo]
- path/to/file.ext: [o que mudou]

### ISSUES NOT ADDRESSED
- [Issue que não pôde ser corrigido neste nível — motivo]
- Se nenhum: "Nenhum"

### NEXT
[Próximo passo: acionar audit.md para re-audit / emitir [ESCALATE] / aguardar instrução]

## RULES
- Fix ONLY the issues listed in audit.md — no additional changes
- Issues must be copied verbatim from audit.md — do not rephrase or interpret
- If a fix requires touching an out-of-scope file → output `[UNCERTAIN: scope]` and stop
- If a fix requires logic changes beyond the issue description → output `[UNCERTAIN: fix]` and stop
- If a fix cannot be applied without scope expansion → output `[ESCALATE]`
- If FIX STATUS is "Bloqueado" for any issue → output `[ESCALATE]`
- If any issue is listed under ISSUES NOT ADDRESSED → output `[ESCALATE]` immediately
- If [ESCALATE] is emitted → do NOT trigger audit.md, stop execution and wait
- Do NOT apply improvements or optimizations beyond what audit.md specified
- Do NOT refactor surrounding code even if it seems related
- After fix is complete and no [ESCALATE] emitted → trigger audit.md for re-audit
