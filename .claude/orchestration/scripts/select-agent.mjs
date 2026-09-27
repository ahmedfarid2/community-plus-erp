#!/usr/bin/env node
/**
 * The delegation router for the global orchestration policy
 * (~/.claude/CLAUDE.md). `selectAgent` is a pure function (no I/O, no
 * clock, no randomness) implementing the routing table, the critical-path
 * dimension floor and the hard-escalation floors. Floors are applied AFTER
 * banding and never lower a band-derived role.
 *
 * Cost discipline: bands 0–4 and 5–9 route to the orchestrator itself
 * (`agent: null`, `inline: true`); band 10–14 roles are advisory
 * (`mandatory: false`); band 15+ and any floor that fired are mandatory.
 *
 * CLI: node select-agent.mjs '<json>'   (or pipe JSON on stdin)
 *   Adds `<project>/.claude/critical-paths.json` (a JSON array of
 *   repo-relative globs) to the defaults, where <project> is
 *   $CLAUDE_PROJECT_DIR or the current directory.
 * Output: one line of JSON, exit 0. Invalid input: `{"error":"…"}`, exit 1.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

// Generic critical surfaces for any stack. A project extends (never
// replaces) these with .claude/critical-paths.json.
export const DEFAULT_CRITICAL_PATHS = [
  "**/auth/**",
  "**/authentication/**",
  "**/authorization/**",
  "**/permissions/**",
  "**/Policies/**",
  "**/payments/**",
  "**/payment/**",
  "**/billing/**",
  "**/checkout/**",
  "**/crypto/**",
  "**/migrations/**",
  "**/firestore.rules",
  "**/storage.rules",
  "**/database.rules.json",
  ".github/workflows/**",
  "**/Dockerfile",
  "**/docker-compose*.yml",
  "ops/**",
  "infra/**",
  "terraform/**",
];

export const DIMENSIONS = [
  "scope",
  "ambiguity",
  "novelty",
  "blastRadius",
  "reversibility",
  "security",
  "coupling",
  "investigation",
  "duration",
];

const TASK_KINDS = ["discovery", "analysis", "planning", "implementation", "review"];

export const MODEL_CLASSES = ["haiku", "sonnet", "opus", "fable"];

const BAND_LABELS = ["0-4", "5-9", "10-14", "15-19", "20-23", "24-27"];

// Mirrors the frontmatter in ~/.claude/agents/; tests/agents.test.mjs
// proves the two are equal, so this cannot drift silently.
export const AGENT_CONFIG = {
  "repository-scout": { model: "haiku", effort: "medium", maxTurns: 15 },
  "system-architect": { model: "opus", effort: "high", maxTurns: 20 },
  "critical-architect": { model: "opus", effort: "xhigh", maxTurns: 25 },
  "fable-strategist": { model: "fable", effort: "xhigh", maxTurns: 30 },
  "fable-rescue": { model: "fable", effort: "max", maxTurns: 60 },
  "sonnet-implementer": { model: "sonnet", effort: "high", maxTurns: 35 },
  "complex-implementer": { model: "sonnet", effort: "xhigh", maxTurns: 50 },
  "standard-reviewer": { model: "sonnet", effort: "high", maxTurns: 20 },
  "critical-reviewer": { model: "opus", effort: "xhigh", maxTurns: 25 },
};

// Rank order per category; `null` (the orchestrator, inline) ranks lowest.
const TIERS = {
  plan: [null, "system-architect", "critical-architect", "fable-strategist", "fable-rescue"],
  implement: [null, "sonnet-implementer", "complex-implementer"],
  review: [null, "standard-reviewer", "critical-reviewer"],
};

// Hard-escalation floors (~/.claude/CLAUDE.md §4). `null` = no floor for
// that category. Implementation never goes past complex-implementer and
// never to a Fable role.
const FLOOR_ROWS = [
  {
    // Only review is floored: the property that matters on a critical
    // surface is an independent, security-minded second look. Planning and
    // implementation follow the (bumped) score like everything else.
    text: "critical surface → critical-reviewer",
    condition: (ctx) => ctx.criticalOverride || ctx.signals.dataLossRisk,
    plan: null,
    implement: null,
    review: "critical-reviewer",
  },
  {
    text: "two or more critical concerns intersect",
    condition: (ctx) => ctx.signals.criticalConcerns >= 2,
    plan: "critical-architect",
    implement: null,
    review: "critical-reviewer",
  },
  {
    text: "critical and unresolved → fable-strategist",
    condition: (ctx) =>
      (ctx.criticalOverride || ctx.signals.criticalConcerns >= 1) &&
      (ctx.signals.ambiguousSystemic || ctx.signals.rootCauseUnknown),
    plan: "fable-strategist",
    implement: "complex-implementer",
    review: "critical-reviewer",
  },
  {
    text: "Sonnet → Opus (two failed attempts or unverifiable root cause)",
    condition: (ctx) => ctx.signals.implementationFailures >= 2 || ctx.signals.rootCauseUnknown,
    plan: "system-architect",
    implement: null,
    review: null,
  },
  {
    text: "Opus → Fable (two failed architecture attempts or invalidated assumptions)",
    condition: (ctx) =>
      ctx.signals.architectureFailures >= 2 || ctx.signals.invalidatedAssumptions >= 2,
    plan: "fable-strategist",
    implement: null,
    review: null,
  },
  {
    text: "rescue: unknown-cause production incident",
    condition: (ctx) =>
      ctx.signals.productionIncident && ctx.signals.rootCauseUnknown && ctx.signals.rescueJustified,
    plan: "fable-rescue",
    implement: null,
    review: null,
  },
];

const REGEX_METACHARS = ".+^${}()|[]\\";

/** Glob → RegExp for repo-relative forward-slash paths. `**∕` matches zero
 *  or more whole directories, so `**∕auth/**` also matches `auth/x.ts`.
 *  Case-insensitive: macOS filesystems are, and framework layouts differ
 *  (Laravel `Modules/Payments`, Flutter `lib/features/payments`). */
export function globToRegExp(pattern) {
  let out = "";
  for (let i = 0; i < pattern.length; i += 1) {
    const c = pattern[i];
    if (c === "*" && pattern[i + 1] === "*") {
      if (pattern[i + 2] === "/") {
        out += "(?:.*/)?";
        i += 2;
      } else {
        out += ".*";
        i += 1;
      }
    } else if (c === "*") {
      out += "[^/]*";
    } else if (c === "?") {
      out += "[^/]";
    } else if (REGEX_METACHARS.includes(c)) {
      out += `\\${c}`;
    } else {
      out += c;
    }
  }
  return new RegExp(`^${out}$`, "i");
}

function rank(category, role) {
  const idx = TIERS[category].indexOf(role ?? null);
  return idx === -1 ? 0 : idx;
}

function applyFloors(category, bandRole, ctx) {
  let bestRole = bandRole;
  let bestRank = rank(category, bandRole);
  const fired = [];
  for (const row of FLOOR_ROWS) {
    const floorRole = row[category];
    if (!floorRole || !row.condition(ctx)) continue;
    fired.push(row.text);
    const floorRank = rank(category, floorRole);
    if (floorRank > bestRank) {
      bestRank = floorRank;
      bestRole = floorRole;
    }
  }
  return { role: bestRole, raised: bestRole !== bandRole, fired };
}

function bandRoleFor(taskKind, bandIndex, signals) {
  const top = signals.rescueJustified ? "fable-rescue" : "fable-strategist";
  switch (taskKind) {
    case "discovery":
      return "repository-scout";
    case "analysis":
      return ["repository-scout", "repository-scout", "system-architect", "critical-architect", "fable-strategist", top][bandIndex];
    case "planning":
      return [null, null, "system-architect", "critical-architect", "fable-strategist", top][bandIndex];
    case "implementation":
      return [null, null, "sonnet-implementer", "complex-implementer", "complex-implementer", "complex-implementer"][bandIndex];
    case "review":
      return [null, null, "standard-reviewer", "critical-reviewer", "critical-reviewer", "critical-reviewer"][bandIndex];
    default:
      return null;
  }
}

function bandIndexOf(score) {
  if (score <= 4) return 0;
  if (score <= 9) return 1;
  if (score <= 14) return 2;
  if (score <= 19) return 3;
  if (score <= 23) return 4;
  return 5;
}

const CATEGORY_OF = {
  discovery: "plan",
  analysis: "plan",
  planning: "plan",
  implementation: "implement",
  review: "review",
};

// One step down the model ladder. Effort cannot be overridden through the
// Agent tool, so an Opus role falling back to Sonnet keeps its own
// (higher) effort and is launched with `model: "sonnet"`.
function fallbackStep(modelClass, agent, taskKind, score) {
  if (modelClass === "fable") {
    return {
      effectiveModelClass: "opus",
      effectiveAgent: "critical-architect",
      modelOverride: null,
      requiresConfirmation: false,
      note: "Fable unavailable: use critical-architect (Opus xhigh), report it, re-evaluate whether the task is safe to continue",
    };
  }
  if (modelClass === "opus") {
    return {
      effectiveModelClass: "sonnet",
      effectiveAgent: agent,
      modelOverride: "sonnet",
      requiresConfirmation: score >= 15,
      note: "Opus unavailable: same role launched with model sonnet; stop for user confirmation on critical work",
    };
  }
  if (modelClass === "haiku") {
    return {
      effectiveModelClass: "sonnet",
      effectiveAgent: "repository-scout",
      modelOverride: "sonnet",
      requiresConfirmation: false,
      note: "Haiku unavailable: repository-scout launched with model sonnet",
    };
  }
  return {
    effectiveModelClass: null,
    effectiveAgent: null,
    modelOverride: null,
    requiresConfirmation: true,
    note:
      taskKind === "implementation"
        ? "no implementation model available; stop"
        : "no substitute model exists for this role; stop",
  };
}

function computeFallback(agent, modelClass, taskKind, score, unavailable) {
  if (!agent || !unavailable.includes(modelClass)) return null;
  let current = fallbackStep(modelClass, agent, taskKind, score);
  let requiresConfirmation = current.requiresConfirmation;
  while (current.effectiveModelClass && unavailable.includes(current.effectiveModelClass)) {
    current = fallbackStep(current.effectiveModelClass, current.effectiveAgent, taskKind, score);
    requiresConfirmation = requiresConfirmation || current.requiresConfirmation;
  }
  return { requestedModelClass: modelClass, requestedAgent: agent, ...current, requiresConfirmation };
}

function validateInput(input) {
  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    throw new Error("input must be a JSON object");
  }
  if (!TASK_KINDS.includes(input.taskKind)) {
    throw new Error(`unknown taskKind: ${JSON.stringify(input.taskKind)} (one of ${TASK_KINDS.join(", ")})`);
  }
  const scores = input.scores;
  if (typeof scores !== "object" || scores === null || Array.isArray(scores)) {
    throw new Error("scores must be an object");
  }
  for (const dim of DIMENSIONS) {
    const value = scores[dim];
    if (!Number.isInteger(value) || value < 0 || value > 3) {
      throw new Error(`invalid or missing score for dimension: ${dim}`);
    }
  }
  const checkPaths = (name, list) => {
    if (!Array.isArray(list) || !list.every((p) => typeof p === "string")) {
      throw new Error(`${name} must be an array of strings`);
    }
    // Repo-relative only: anything else would silently never match a glob.
    const bad = list.find((p) => path.isAbsolute(p) || p.startsWith("./") || p.includes("\\"));
    if (bad !== undefined) {
      throw new Error(`${name} must be repo-relative (no absolute path, "./" prefix or backslash): ${JSON.stringify(bad)}`);
    }
    return list;
  };
  const paths = checkPaths("paths", input.paths ?? []);
  const extraCriticalPaths = checkPaths("extraCriticalPaths", input.extraCriticalPaths ?? []);
  const signals = input.signals ?? {};
  if (typeof signals !== "object" || signals === null || Array.isArray(signals)) {
    throw new Error("signals must be an object");
  }
  const unavailable = input.unavailable ?? [];
  if (!Array.isArray(unavailable) || !unavailable.every((v) => MODEL_CLASSES.includes(v))) {
    throw new Error(`unavailable must be an array drawn from: ${MODEL_CLASSES.join(", ")}`);
  }
  return { taskKind: input.taskKind, scores, paths, extraCriticalPaths, signals, unavailable };
}

/** Pure. Deterministic. */
export function selectAgent(input) {
  const { taskKind, scores, paths, extraCriticalPaths, signals: rawSignals, unavailable } =
    validateInput(input);
  const signals = {
    implementationFailures: 0,
    architectureFailures: 0,
    invalidatedAssumptions: 0,
    criticalConcerns: 0,
    rootCauseUnknown: false,
    productionIncident: false,
    dataLossRisk: false,
    rescueJustified: false,
    ambiguousSystemic: false,
    ...rawSignals,
  };

  const criticalRegexps = [...DEFAULT_CRITICAL_PATHS, ...extraCriticalPaths].map(globToRegExp);
  const matchedCriticalPaths = paths.filter((p) => criticalRegexps.some((re) => re.test(p)));
  const criticalOverride = matchedCriticalPaths.length > 0;

  const scoreInput = DIMENSIONS.reduce((sum, d) => sum + scores[d], 0);
  const adjusted = { ...scores };
  if (criticalOverride) {
    adjusted.blastRadius = Math.max(adjusted.blastRadius, 2);
    adjusted.security = Math.max(adjusted.security, 2);
  }
  const score = DIMENSIONS.reduce((sum, d) => sum + adjusted[d], 0);
  const bandIndex = bandIndexOf(score);
  const band = BAND_LABELS[bandIndex];

  const ctx = { criticalOverride, signals };
  const category = CATEGORY_OF[taskKind];
  const bandRole = bandRoleFor(taskKind, bandIndex, signals);
  // Discovery always goes to the scout; floors are still evaluated so the
  // caller sees which escalations the upcoming plan will face.
  const floored =
    taskKind === "discovery"
      ? { role: bandRole, raised: false, fired: applyFloors("plan", null, ctx).fired }
      : applyFloors(category, bandRole, ctx);

  const agent = floored.role;
  const escalation = floored.fired.length > 0 ? floored.fired.join("; ") : null;
  const config = agent ? AGENT_CONFIG[agent] : null;
  const modelClass = config ? config.model : null;
  const mandatory = agent !== null && taskKind !== "discovery" && (bandIndex >= 3 || floored.raised);

  let reason = agent
    ? `Band ${band} ${taskKind} → ${agent}${mandatory ? " (mandatory)" : " (advisory: delegate only if it earns its cost)"}.`
    : `Band ${band} ${taskKind} stays inline with the orchestrator.`;
  if (escalation) reason += ` Escalations: ${escalation}.`;

  return {
    agent,
    inline: agent === null,
    mandatory,
    modelClass,
    effort: config ? config.effort : null,
    maxTurns: config ? config.maxTurns : null,
    reason,
    taskKind,
    scoreInput,
    score,
    band,
    criticalOverride,
    matchedCriticalPaths,
    escalation,
    fallback: computeFallback(agent, modelClass, taskKind, score, unavailable),
  };
}

function loadProjectCriticalPaths() {
  const dir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
  try {
    const list = JSON.parse(readFileSync(path.join(dir, ".claude", "critical-paths.json"), "utf8"));
    return Array.isArray(list) ? list.filter((p) => typeof p === "string") : [];
  } catch {
    return [];
  }
}

function runCli() {
  let parsed;
  try {
    const raw = typeof process.argv[2] === "string" ? process.argv[2] : readFileSync(0, "utf8");
    parsed = JSON.parse(raw);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({ error: `invalid input: ${error.message}` })}\n`);
    process.exitCode = 1;
    return;
  }
  try {
    const extra = [...(parsed?.extraCriticalPaths ?? []), ...loadProjectCriticalPaths()];
    const result = selectAgent({ ...parsed, extraCriticalPaths: extra });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({ error: error.message })}\n`);
    process.exitCode = 1;
  }
}

const isMain =
  typeof process.argv[1] === "string" && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) runCli();
