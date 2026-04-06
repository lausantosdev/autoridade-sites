# .agent/escalation.md

## PURPOSE
Define the escalation protocol when Gemini cannot resolve an issue.
Escalation hands off audit responsibility to Sonnet.
Sonnet audits and produces findings — Gemini Agent applies the final fix.

## TRIGGER CONDITIONS
Escalation is activated when ANY of the following is true:
- Output contains `[ESCALATE]`
- Same issue persists after 2 fix attempts
- Behavior is inconsistent or non-deterministic
- Diff is suspicious or larger than expected
- Logic is critical (auth, DB, core business logic)
- Audit is inconclusive
- Fix loop repeats more than twice
- Issue listed under ISSUES NOT ADDRESSED in fix.md

## INPUT REQUIRED
- plan.md output (approved plan)
- report.md output (last execution report)
- audit.md output (last audit — if available)
- fix.md output (last fix attempt — if available)
- git diff (current state — source of truth)

## OUTPUT LANGUAGE
Always generate escalation output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT (SONNET OUTPUT)

### ESCALATION STATUS
[Solução Encontrada / Sem Solução / Requer intervenção manual]

### ESCALATION REASON
[Por que o Gemini não conseguiu resolver — contexto objetivo]

### FINDINGS
- [Problema identificado — arquivo, linha, comportamento, impacto]

### ROOT CAUSE
[Causa raiz do problema — não apenas o sintoma]

### FIX RECOMMENDATIONS
- [Recomendação de correção — o quê, onde, como]
- Sonnet recomenda — Gemini Agent executa

### RISK ASSESSMENT
[Risco de aplicar o fix recomendado — baixo / médio / alto]
- Motivo objetivo

### NEXT
[Próximo passo: Gemini Agent aplica fix / requer intervenção manual / re-audit por Sonnet]

## RULES
- Sonnet audits only — it does NOT execute fixes
- Gemini Agent applies fixes based on Sonnet findings
- If ESCALATION STATUS is "Sem Solução" → output `[ESCALATE: manual]` and stop all automation
- If ESCALATION STATUS is "Solução Encontrada" → Gemini Agent applies FIX RECOMMENDATIONS
- If RISK ASSESSMENT is "alto" → output `[ESCALATE: manual]` and require human approval
- After Gemini applies fix → optional re-audit by Sonnet before commit
- If re-audit by Sonnet finds same issue persisting → output `[ESCALATE: manual]`
- `[ESCALATE: manual]` is the final state — no further automation, human must intervene
