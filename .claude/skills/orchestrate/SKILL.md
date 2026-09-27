---
name: orchestrate
description: Run a substantive engineering task through the full orchestration state machine — classify, route with the router, delegate bounded work to the global agents, verify, get an independent review, and close with the right report. Use when the user types /orchestrate, or for any task likely to score 10+ (multi-module, critical surface, unclear root cause).
argument-hint: <task description>
---

Run the orchestration policy in `.claude/orchestration/POLICY.md` for this task:

> $ARGUMENTS

Announce each transition in one line.

1. **INTAKE** — restate the deliverable and non-goals; note open questions for the user. Read the project's `CLAUDE.md` for its validation commands and sensitive areas.
2. **CLASSIFY** — score the nine dimensions (0–3). If the total is clearly under 10 and no critical path is touched, say `Score N/27, no critical triggers — implementing directly.` and just do the task well. Otherwise read `.claude/orchestration/README.md`, run the router for each phase you intend to delegate (`node .claude/orchestration/scripts/select-agent.mjs '<json>'`, repo-relative `paths`), and print the delegation decision record (README §2). Say whether ultracode would materially help; if so and it isn't on, tell the user before implementing.
3. **DISCOVER** — direct reads, or `repository-scout` when the lookup would flood your context. Separate verified facts from assumptions.
4. **PLAN** — inline below 10; otherwise the routed architect with the handoff contract (README §1). Fable roles need the `FABLE_ESCALATION` line (README §4) and only ever plan.
5. **IMPLEMENT** — inline below 10; `sonnet-implementer` / `complex-implementer` as routed at 10+. One owner per overlapping file set. An agent's `STOP:` request comes back to you to resolve and resume.
6. **VERIFY** — run the project's validation yourself; keep the verbatim output and `git rev-parse HEAD` + clean/dirty state.
7. **INDEPENDENT REVIEW** — routed reviewer gets requirement, contract, acceptance criteria, diff range and verbatim validation output — not the implementer's self-assessment. A critical-path match means `critical-reviewer` runs whatever the score.
8. **RESOLVE FINDINGS** — fix Blocker/High; decide Medium/Low explicitly.
9. **FINAL VERIFICATION** — re-run affected validation; confirm the diff has only explained changes.
10. **COMPLETE** — report proportional to score: a few lines below 15; the full report (README §5) at 15+, naming resolved models only from observable evidence and every fallback.

Never: skip a state silently, downgrade critical work silently, set session effort/ultracode from here, run two editing agents on overlapping files, or let an agent delegate.
