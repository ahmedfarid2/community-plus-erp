# Orchestration reference (global)

Read on demand — for score 10+ tasks or any Fable role. The binding policy
is `.claude/orchestration/POLICY.md`; this file holds the templates and mechanics it
points to. Consolidated 2026-09-27 from the per-repo setups in
`applyni`, `ibdaa-course` and the template repos (`ahmedfarid2`,
`cairo-plaza`, `digit-dental`, `itqan-dental`, `ofoq`,
`reform-dental-concept`, `ahmedfarid2.github.io`).

## Layout

```
.claude/orchestration/POLICY.md                     global policy (loaded everywhere)
.claude/agents/*.md                   the nine roles
~/.claude/settings.json                 hooks + permissions.ask gates
~/.claude/skills/orchestrate/           /orchestrate <task>
~/.claude/skills/new-project/           /new-project — bootstrap a project CLAUDE.md
.claude/orchestration/
  bin/hook                              finds node (nvm-safe), runs a script, fails open
  scripts/select-agent.mjs              router (CLI + pure function)
  scripts/readonly-bash-guard.mjs       PreToolUse Bash: read-only roles → inspection allowlist
  scripts/readonly-edit-guard.mjs       PreToolUse Edit/Write: read-only roles denied
  scripts/fable-gate.mjs                PreToolUse Agent: single delegator + Fable evidence gate
  scripts/lifecycle-log.mjs             SubagentStart/Stop → runtime/lifecycle.jsonl
  scripts/vendor.mjs                    copy the setup into a repo (for cloud sessions)
  tests/                                node --test .claude/orchestration/tests
  runtime/lifecycle.jsonl               delegation log, all projects (not a secret store)
```

## 1. Handoff contract (every delegation prompt, score 10+)

```
Objective: <one sentence>
Context: <only what this agent needs>
In scope: <files / modules>
Out of scope: <what not to touch or investigate>
Constraints: <repo rules, compatibility, no migrations, …>
Expected output: <format / sections>
Acceptance criteria: <checkable statements>
Editing allowed: yes (files: …) | no
Validation required: <commands>
Validation ran against: <sha> (tree: clean|dirty)     ← reviewers
Validation output: <verbatim, or "none">              ← reviewers
Stop and escalate when: <conditions>
```

Reviewers get the requirement, contract, acceptance criteria, diff range
and validation output — **not** the implementer's self-assessment.

## 2. Delegation decision record (print before delegating, score 10+)

```
TASK: <one line>
SCORES: <nine raw> → <adjusted, if a critical path floored them>
HARD TRIGGERS: <rules fired, or none>
PLANNER: <agent | inline> (<model>/<effort>)
IMPLEMENTER: <agent | inline> (<model>/<effort>)
REVIEWER: <agent | self> (<model>/<effort>)
SCOPE / OUT OF SCOPE: <…>
WHY: <one line>
```

## 3. Router

```bash
node .claude/orchestration/scripts/select-agent.mjs '{"taskKind":"implementation","scores":{"scope":1,"ambiguity":1,"novelty":1,"blastRadius":1,"reversibility":1,"security":1,"coupling":1,"investigation":1,"duration":1},"paths":["src/auth/session.ts"]}'
```

- `taskKind`: discovery | analysis | planning | implementation | review.
- `paths`: repo-relative, forward slashes, no `./` — anything else is
  rejected (it would silently never match).
- `signals` (all optional): `implementationFailures`, `architectureFailures`,
  `invalidatedAssumptions`, `criticalConcerns` (ints); `rootCauseUnknown`,
  `productionIncident`, `dataLossRisk`, `rescueJustified`,
  `ambiguousSystemic` (bools).
- `unavailable`: model classes observed unavailable → `fallback` object
  (effective agent, `modelOverride` to pass to the Agent tool, whether user
  confirmation is required).
- Output: `agent` (`null` = do it inline), `mandatory` (false = advisory,
  delegate only if it earns its cost), model/effort/maxTurns, score, band,
  matched critical paths, escalations fired.
- Critical paths = built-in generic globs + `<project>/.claude/critical-paths.json`
  (a JSON array of repo-relative globs, e.g. `["lib/services/payment_*.dart"]`).

## 4. Fable escalation evidence

A Fable role (`fable-strategist`, `fable-rescue`) or any `model: fable`
override needs exactly one line in the Agent prompt:

```
FABLE_ESCALATION: {"fable_escalation":true,"reason":"two Opus xhigh passes produced conflicting root causes for the double-send","score":22,"assignment":"planning","no_implementation":true,"prior_attempts":["critical-architect pass 1: lock ordering","critical-architect pass 2: retry idempotency; contradicts pass 1"]}
```

`reason` ≥ 20 chars; `score` 0–27; `assignment` `planning` | `rescue`
(`fable-rescue` requires `rescue`); `no_implementation: true`; plus
`opus_insufficient_because` (≥ 20 chars) or non-empty `prior_attempts`.
The gate also denies prompts containing implementation markers
(`Editing allowed: yes`, "apply the patch", "write the code", "edit the
files"), `model: fable` on a non-Fable role, and any nested Agent call from
one of the roles.

## 5. Final report (score 15+)

1. Nine dimension scores · 2. Risk score and band · 3. Hard triggers ·
4–6. Planning / implementation / review model and effort · 7. Resolved
models where observable (`/tasks`), else "not verified" · 8. Fallbacks or
substitutions · 9. Agents used and why · 10. Files changed ·
11. Implementation summary · 12–13. Validation commands and verbatim
results · 14–15. Reviewer findings by severity and how each was resolved ·
16. Remaining risks · 17. Manual checks still required · 18. Whether
ultracode was considered.

Score 10–14: files changed, validation and result, any risk — a few lines.

## 6. Model availability

- `fable` is a family alias (currently Fable 5.1 on Claude Code 2.1.283;
  the CLI's `best` alias also maps to `fable`). Frontmatter never carries a
  versioned id.
- Observe, never probe: session info, `/status`, `/tasks`, and warnings
  like "isn't available for your account" or "not in the availableModels
  allowlist". A hook records the *requested* model only.
- Fable unavailable → `critical-architect` (Opus xhigh), report it,
  re-evaluate safety. Opus unavailable → same role with `model: "sonnet"`,
  stop for confirmation on critical work. Haiku → Sonnet. No Sonnet → stop.

## 7. Using it in a repository

- **On this laptop**: nothing to do — every project gets the global setup.
  Add a project `CLAUDE.md` with facts (use `/new-project`), and optionally
  `.claude/critical-paths.json`.
- **For cloud sessions / other machines**: vendor it into the repo:
  `node .claude/orchestration/scripts/vendor.mjs <repo> --check` to see
  drift, then without `--check` to write. It overwrites the nine agent
  files, copies the scripts, the policy (`.claude/orchestration/POLICY.md`),
  this reference and `/orchestrate` with repo-relative paths, merges hooks
  and `permissions.ask` into `.claude/settings.json`, and flags old agent
  files whose project facts must move into `CLAUDE.md`. The project's
  `CLAUDE.md` then needs one line: `@.claude/orchestration/POLICY.md`.
- **Not vendored on purpose: `applyni`.** It has its own stricter 11-agent
  system (router with Applyni's critical paths, `pnpm test:delegation`
  pinning its files) that this global setup was derived from; overwriting
  it would break that gate. On this laptop the global hooks run beside its
  own, with identical rules.

## Known limits

- **The Bash allowlist is fail-open.** It keys on `agent_type` in the
  PreToolUse payload; if a Claude Code upgrade stops sending it, read-only
  roles silently regain full Bash. After each upgrade, delegate to
  `standard-reviewer` and confirm `npm test` and `git push --dry-run` are
  denied with a `[code:…]` reason while `git status` works. Last verified
  by applyni on 2.1.257 (2026-09-21); re-check on 2.1.283.
- **Workflow scripts bypass the Agent hook** (`agent()` doesn't go
  through the Agent tool). By policy only: no Fable model and no Fable
  implementation work inside a Workflow.
- **The `SubagentStop` hook also fires when the main session's turn ends**
  (no `agent_type`); the logger drops those lines.
- Hooks and agent files load at session start: edits apply to new sessions.
- If node can't be found, `bin/hook` exits 0 and the guards are off —
  `tests/` includes a check that it finds node.
