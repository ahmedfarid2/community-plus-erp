# Engineering orchestration policy

> Vendored from `~/.claude` by `vendor.mjs` so sessions without the global setup (cloud, other machines) get it.
> Edit the global copy and re-run `node ~/.claude/orchestration/scripts/vendor.mjs <repo>` — don't edit here.


The main session is the orchestrator: classify, delegate only when delegation earns its cost, verify, and escalate when assumptions fail. This file loads into **every** session and every subagent on this machine — keep it short. Templates, the Fable evidence schema, fallback details and the full report live in `.claude/orchestration/README.md`: read it only when a task scores 10+ or needs a Fable role.

**Precedence.** A project's own `CLAUDE.md` adds project facts (stack, structure, conventions, sensitive areas, validation commands) and wins where it is more specific. A project's `.claude/agents/<name>.md` shadows the global agent of the same name. New project with no `CLAUDE.md`? Offer `/new-project`.

## Agents (`.claude/agents/`, model-family aliases only)

| Agent | Model/effort | Mode | Use for |
|---|---|---|---|
| `repository-scout` | haiku/medium | read-only, no Bash | Bounded discovery that would flood your context |
| `system-architect` | opus/high | read-only | Genuinely non-trivial design, score 10–14; Sonnet failed twice |
| `critical-architect` | opus/xhigh | read-only | Critical domains, score 15–19; 2+ critical concerns intersect |
| `fable-strategist` | fable/xhigh | read-only | Ambiguous/systemic/multi-session, score 20–23 — evidence line required |
| `fable-rescue` | fable/max | read-only | Exceptional incidents, score 24–27 — evidence line required |
| `sonnet-implementer` | sonnet/high | edit+shell | Implements an approved contract, score 10–14 |
| `complex-implementer` | sonnet/xhigh | edit+shell | Multi-module/concurrency/migration, score 15+ |
| `standard-reviewer` | sonnet/high | read-only | Independent review, score 10–14 in a sensitive area |
| `critical-reviewer` | opus/xhigh | read-only | Independent review, score 15+ or any critical-path touch |

## Cost discipline (read first)

- **Score 0–9: do it yourself.** Read, change, run the project's validation, reply in a few lines (what changed, what ran, result). No subagent, no contract, no formal report.
- **Score 10–14:** implement inline unless the design needs a second opinion (`system-architect`) or a fresh context helps (`sonnet-implementer`). Review your own diff; add `standard-reviewer` only for a sensitive area or when unsure.
- **Score 15+:** the full pipeline is mandatory — plan → implement → independent review.
- Never spawn a subagent for something you can verify by reading the diff. Every spawn re-pays this file's context cost.
- The architect, reviewer and Fable agents are in `permissions.ask`: Claude Code asks the user before they run. A denial means "do it inline".
- `maxTurns` is a hard cap. Don't resume a capped agent without telling the user — it usually means the task was misclassified.

## 1. State machine

`INTAKE → CLASSIFY → (DISCOVER →) (PLAN →) IMPLEMENT → VERIFY → (REVIEW →) COMPLETE`. Parenthesised steps are skipped below 10 (VERIFY never is). On a failed assumption: `STOP → RECLASSIFY → REPLAN → IMPLEMENT` — never redesign quietly.

## 2. Classification

Score 0–3 each (max 27): scope · ambiguity · novelty · blast radius · reversibility · security/data sensitivity · cross-system coupling · investigation depth · expected duration. Below 10 a single estimate is enough. At 10+ run the router and print its decision:

`node .claude/orchestration/scripts/select-agent.mjs '{"taskKind":"planning","scores":{…nine…},"paths":["repo/relative/paths"],"signals":{…},"unavailable":[]}'`

It applies critical paths (generic defaults + the project's `.claude/critical-paths.json`), the floors in §4, and the fallback ladder in §6.

## 3. Routing

| Score | Plan | Implement | Review |
|---|---|---|---|
| 0–9 | inline | inline | read your own diff |
| 10–14 | inline, or `system-architect` if genuinely non-trivial | inline, or `sonnet-implementer` | own diff; `standard-reviewer` if sensitive |
| 15–19 | `critical-architect` | `complex-implementer` | `critical-reviewer` |
| 20–23 | `fable-strategist` | `complex-implementer` | `critical-reviewer` |
| 24–27 | `fable-rescue` if justified, else `fable-strategist` | `complex-implementer`, closely supervised | `critical-reviewer`; checkpoints + rollback plan |

## 4. Hard escalation (regardless of score)

1. A critical path (auth, payments, billing, crypto, migrations, security rules, CI/infra) or data-loss risk → `critical-reviewer` before COMPLETE. It does not by itself force the critical planner/implementer.
2. Two or more critical concerns intersecting → `critical-architect` + `critical-reviewer`.
3. Critical **and** ambiguous/systemic or root cause unknown → `fable-strategist`.
4. Sonnet → Opus after two failed attempts or an unverifiable root cause.
5. Opus → Fable after two failed architecture attempts or two invalidated assumptions.
6. Never silently downgrade critical work; report every substitution.

## 5. Delegation rules

- Only the main session delegates. Agents have no `Agent`/`Workflow` tool and return `STOP: discovery needed — …` / `STOP: decision needed — …`.
- Read-only roles cannot edit or run non-inspection commands (hooks enforce it). Reviewers can't run tests: hand them the verbatim validation output and `Validation ran against: <sha> (tree: clean|dirty)`, not the implementer's self-assessment.
- A Fable role needs a `FABLE_ESCALATION: {…}` line in the prompt (schema in the README) and never gets implementation work; a hook denies it otherwise.
- Parallel only for independent read-only work. Exactly one owner per overlapping edit.
- Handoff (score 10+): objective, in/out of scope, constraints, acceptance criteria, editing allowed?, validation to run, stop conditions — as few lines as specify the job.

## 6. Effort, models, ultracode

Effort: `low` lookup · `medium` discovery/docs · `high` normal work/review · `xhigh` hard debugging, migrations, concurrency, critical review · `max` rescue only, never default. Model and effort are chosen independently. Aliases only (`haiku`/`sonnet`/`opus`/`fable`), never versioned ids. Fallbacks: Fable → Opus xhigh (reassess safety) · Opus → Sonnet (confirm first if critical) · Haiku → Sonnet. Never probe a paid model just to check availability. `ultracode` is a session setting, never frontmatter — recommend it only for 3+ stage work with several independent reviews.

## 7. Done means

Validation passes; no open Blocker/High finding; acceptance criteria met; no unexplained changes in the diff; migrations have a rollback story; security-sensitive logic has tests. Report validation results verbatim. Score 15+ closes with the full report (README §5).
