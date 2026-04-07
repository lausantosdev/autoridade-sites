# .agent/audit.md

## PURPOSE
Verify that execution matches the plan and the report is consistent with the diff.
The auditor identifies issues and suggests fixes — it does NOT execute anything.
Audit is performed by Gemini CLI (default) or Sonnet (escalation).

## INPUT REQUIRED
- plan.md output (approved plan)
- report.md output (execution report)
- git diff (source of truth)

## OUTPUT LANGUAGE
Always generate audit output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### AUDIT STATUS
[Aprovado / Aprovado com ressalvas / Reprovado]

### DIFF VS REPORT
[O git diff é consistente com o FILES MODIFIED e DIFF SUMMARY do report?]
- Sim / Não — detalhar divergências por arquivo

### PLAN VS EXECUTION
[O que foi executado corresponde exatamente ao que foi planejado?]
- Sim / Não — detalhar desvios por step

### VALIDATION CHECK
[O EXPECTED OUTCOME do plano foi atingido com base no diff?]
- Sim / Não / Parcialmente — motivo objetivo

### ISSUES FOUND
- [Descrição objetiva do problema — arquivo, linha, comportamento]
- Se nenhum: "Nenhum"

### FIX SUGGESTIONS
- [Sugestão de correção por issue — o quê mudar, onde, por quê]
- O auditor sugere — NÃO executa
- Se nenhum: "Nenhum"

### NEXT
- If AUDIT STATUS is "Aprovado" → trigger commit.md
- If AUDIT STATUS is "Aprovado com ressalvas" → trigger fix.md for minor corrections only; if corrections are not minor → [ESCALATE]
- If AUDIT STATUS is "Reprovado" → trigger fix.md

## RULES
- git diff is the source of truth — report and plan are verified against it, not the reverse
- If DIFF VS REPORT diverges → output `[UNCERTAIN: diff]` and detail all divergences
- If ISSUES FOUND are unresolvable at Gemini level → output `[ESCALATE]`
- If AUDIT STATUS is "Reprovado" → trigger fix.md, do NOT approve commit
- If AUDIT STATUS is "Aprovado com ressalvas" → trigger fix.md for minor corrections only; if corrections are not minor → output `[ESCALATE]`
- If AUDIT STATUS is "Aprovado" → Gemini Agent may proceed to commit
- The auditor must NEVER suggest scope expansion in FIX SUGGESTIONS
- Fix suggestions must be minimal and targeted — patch only what is broken
- If this is a re-audit after fix.md → compare against previous audit output and note deltas
- If this is a re-audit after fix.md AND the same issue persists → output `[ESCALATE]`
