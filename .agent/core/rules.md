# .agent/rules.md

## EXECUTION CONSTRAINTS

- Execute ONLY what is defined in the current task
- Do NOT infer, expand, or extend scope beyond explicit instructions
- Do NOT refactor, rename, or reorganize unrelated code
- Do NOT create files not required by the task
- Treat the task definition as the contract — nothing more

## SCOPE CONTROL

- Before acting: confirm which files are in scope
- List ALL files that will be modified before making changes
- If a fix requires touching an out-of-scope file → STOP and report
- If completing the task requires scope expansion → flag it, do not proceed

## BEHAVIOR RULES (GEMINI AGENT)

- Always generate a PLAN before executing (following `plan.md` format)
- Always generate a REPORT after executing (following `report.md` format)
- Reports must include: files modified, what changed, why, and diff summary
- Fixes must be minimal and targeted — touch only what is broken
- Do NOT re-execute the full task when fixing — patch only the failing part
- Do NOT commit without a passing audit

## SAFETY RULES

- Never delete or overwrite files outside task scope
- Never modify auth, DB schema, or core logic without Sonnet-level audit
- Never assume a fix is correct — validate against the original objective
- If a fix introduces new behavior → flag it before applying
- Treat git diff as source of truth, not the report

## DECISION RULES (WHEN UNCERTAIN)

- If uncertain about scope → stop, report, and ask
- If uncertain about correctness → output `[UNCERTAIN]` and state the reason explicitly
- If the same issue persists after 2 fix attempts → output `[ESCALATE]` and stop
- If behavior is inconsistent across runs → output `[ESCALATE]` and stop
- If audit is inconclusive → output `[ESCALATE]` and stop
- Default: solve at lowest level possible; escalate only when necessary

## ESCALATION TRIGGERS

Escalate to Sonnet if ANY of the following is true:
- Output contains `[ESCALATE]`
- Issue persists after fix
- Behavior is inconsistent or non-deterministic
- Diff is suspicious or larger than expected
- Logic is critical (auth, DB, core business logic)
- Audit is inconclusive
- Gemini shows uncertainty
- Fix loop repeats more than twice
