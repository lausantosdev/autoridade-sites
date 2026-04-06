# .agent/self-audit.md

## PURPOSE
Allow Gemini Agent to verify its own output before triggering audit.md.
Self-audit is a lightweight internal check — not a substitute for audit.md.
Goal: catch obvious errors early and reduce unnecessary audit cycles.

## INPUT REQUIRED
- plan.md output
- report.md output
- git diff (updated state)

## OUTPUT LANGUAGE
Always generate self-audit output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### SELF-AUDIT STATUS
[Aprovado / Reprovado]

### PLAN COMPLIANCE
[A execução seguiu exatamente o plan.md?]
- Sim / Não — detalhar desvios por step

### SCOPE COMPLIANCE
[Apenas os arquivos em escopo foram modificados?]
- Sim / Não — listar arquivos fora de escopo tocados

### DIFF CHECK
[O git diff corresponde ao que foi declarado no report.md?]
- Sim / Não — detalhar divergências

### EXPECTED OUTCOME CHECK
[O resultado atende ao EXPECTED OUTCOME definido no plano?]
- Sim / Não / Parcialmente — motivo objetivo

### RED FLAGS
- [Qualquer comportamento suspeito, efeito colateral, ou mudança inesperada]
- Se nenhum: "Nenhum"

### NEXT
[Próximo passo: acionar audit.md / emitir tag / corrigir antes de prosseguir]

## RULES
- Self-audit must be performed after exec.md and before audit.md
- Self-audit does NOT replace audit.md — it precedes it
- If PLAN COMPLIANCE is "Não" → output `[UNCERTAIN: deviation]` and stop
- If SCOPE COMPLIANCE is "Não" → output `[UNCERTAIN: scope]` and stop
- If DIFF CHECK is "Não" → output `[UNCERTAIN: diff]` and stop
- If EXPECTED OUTCOME CHECK is "Parcialmente" → document clearly and proceed to audit.md
- If EXPECTED OUTCOME CHECK is "Não" → output `[UNCERTAIN: outcome]` and stop
- If any RED FLAGS are critical → output `[ESCALATE]`
- If SELF-AUDIT STATUS is "Aprovado" → trigger audit.md
- If SELF-AUDIT STATUS is "Reprovado" → do NOT trigger audit.md, stop and report
- Keep this check fast and focused — do not over-analyze
