## PURPOSE
Run a macro-level health check on the project and the agent system.
Triggered every 5 complete cycles — not per task.
Goal: identify accumulating issues before they become blockers.

## INPUT REQUIRED
- `context.md` current state
- Recent `audit.md` outputs (last N cycles)
- Recent `fix.md` outputs (last N cycles)
- Git log (last N cycles)

## OUTPUT LANGUAGE
Always generate health output in Brazilian Portuguese (pt-BR).
Headers remain in English — structural anchors.
File paths, code identifiers, and tags remain in their original form.

## FORMAT

### CODE HEALTH
- Arquivos órfãos identificados: [listar ou "Nenhum"]
- Dependências desatualizadas: [listar ou "Nenhum"]
- TODOs acumulados: [listar por arquivo ou "Nenhum"]

### AGENT SYSTEM HEALTH
- `[UNCERTAIN]` recorrentes: [padrão identificado ou "Nenhum"]
- `[ESCALATE]` recorrentes: [padrão identificado ou "Nenhum"]
- `context.md` atualizado: [Sim / Não — detalhar se Não]
- Fix loops frequentes: [padrão identificado ou "Nenhum"]

### PROCESS HEALTH
- Tempo médio plan → commit: [estimativa baseada no git log]
- Tasks mal dimensionadas: [identificadas ou "Nenhuma"]
- Re-audits frequentes: [padrão identificado ou "Nenhum"]

### RECOMMENDATIONS
- [Ação sugerida — descrição objetiva]
- Prioridade: [Alta / Média / Baixa]
- If none: "Nenhuma"

## RULES
- Triggered every 5 complete cycles — counter maintained in `context.md`
- Not triggered per task — out-of-band execution only
- Does not block or modify any active cycle
- Does not modify any file in `core/`
- If CODE HEALTH reveals critical issues → flag with priority Alta in RECOMMENDATIONS
- If AGENT SYSTEM HEALTH reveals recurring `[ESCALATE]` pattern → flag with priority Alta in RECOMMENDATIONS
- Output is observational only — no automatic fixes are applied
- After health output is generated → human reviews RECOMMENDATIONS and decides next action
