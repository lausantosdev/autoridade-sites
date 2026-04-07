# AGENT.md

## PURPOSE
Bootstrap of the autonomous agent system.
First file read in every session, no exceptions.
Summarizes critical rules and defines the roles of each agent.
Maximum 200 lines — never grow beyond this.

## FOLDER PARADIGM

- `.agent/core/` — immutable engine instructions; shielded during execution; no agent writes here
- `.agent/memory/` — dynamic records; read and written every cycle

## AGENT ROLES

- Gemini Agent — plan, execute, fix, commit; never modifies `core/`
- Gemini CLI — audit (default); never executes code
- Claude Sonnet — escalation, root cause, findings; triggered only via `[ESCALATE]`
- Human — final approval, intervention, rollback; triggered via `[ESCALATE: manual]`

## CYCLE FLOW

- Mandatory read: `memory/context.md`
- Step zero: `spec.md` (without approved spec, plan.md is not generated)
- Main flow: `spec.md → plan.md → exec.md → self-audit.md → report.md → audit.md`
- Fix: `fix.md` — max 2x; on third failure emit `[ESCALATE]` automatically
- Escalation: `escalation.md` → `rollback.md` (if terminal)
- Closing: `commit.md → CHANGELOG → context.md (update)`
- Health: `health.md` every 5 complete cycles — out-of-band, not triggered per task

## TASK-ID PROTOCOL

- Generated exclusively in `spec.md`
- Mandatory format: `YYYYMMDD-KEYWORD`
- Travels strictly in cascade through all cycle files: `spec → plan → exec → report → audit → fix → commit`
- Mandatory header in every file of the cycle: `TASK-ID: YYYYMMDD-KEYWORD`

## MECHANICAL TAGS

- `[ESCALATE]` — escalate to Claude Sonnet; emit and stop
- `[ESCALATE: manual]` — terminal state; all automation stops; human intervenes
- `[UNCERTAIN: reason]` — explicit uncertainty; stop immediately; report reason

## LANGUAGE CONVENTIONS

- Structural headers → English (anchors for CLI Regex)
- Body content → pt-BR (readable for the human operator)
- Mechanical tags → always English

## RULES

- `memory/context.md` must be read before any cycle, no exceptions
- Without approved `spec.md` → `plan.md` is not generated
- Max 2x fix loop → on third failure emit `[ESCALATE]` automatically
- `ISSUES NOT ADDRESSED` in `fix.md` → immediate `[ESCALATE]`, no re-audit
- Git diff is the source of truth — never the report
- `context.md` must never exceed 150 lines (alert at 120)
- No agent modifies files in `core/` during execution
- `health.md` runs every 5 complete cycles — counter maintained in `context.md`
- If the previous task ended with `[ESCALATE: manual]` → `rollback.md` must be executed and `context.md` updated before any new `spec.md` is opened
