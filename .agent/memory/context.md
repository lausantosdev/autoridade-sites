## PURPOSE
Persistent ledger between sessions.
Records decisions, constraints, and open questions so the agent does not lose context across cycles.
Mandatory read at the start of every cycle, before spec.md.
This is a living file — designed for constant reading and **writing**.

## CYCLE COUNTER
Total de ciclos completos: 0
Próximo health.md em: 5

## DECISIONS LOG
- [Nenhuma decisão registrada ainda]

## KNOWN CONSTRAINTS
- [Nenhuma restrição identificada ainda]

## OPEN QUESTIONS
- [Nenhuma pergunta em aberto]

## RULES
- Maximum 150 lines — alert threshold at 120
- Must be updated after every commit (via commit.md)
- Must be updated after every rollback (via rollback.md)
- Read at the beginning of every cycle, before spec.md
- If total lines > 120 → commit.md applies pruning to the DECISIONS LOG
- Consolidated entries use prefix: `[consolidated] tópico — rationale unificado`
- Never exceed 150 lines under any circumstance
