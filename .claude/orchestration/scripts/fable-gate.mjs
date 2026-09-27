#!/usr/bin/env node
/**
 * PreToolUse hook for the Agent tool. Enforces three things:
 *   1. Single delegator — none of the orchestration agents (global or project copies) may
 *      make a nested Agent call (they have no Agent tool either, so this
 *      is defence in depth against a future tool-list mistake).
 *   2. A Fable model (`fable`/`best`) is never used on a non-Fable role.
 *   3. A Fable role is never invoked without machine-readable escalation
 *      evidence, and never given implementation work.
 *
 * Stdin: the PreToolUse JSON payload for an Agent call. Stdout: nothing,
 * or exactly one deny object. Exit: always 0.
 *
 * This hook reads `tool_input.prompt` only to run the marker regexes and
 * to extract the evidence line. It never logs, echoes or includes prompt
 * text or evidence *values* in a deny reason — only field names and
 * codes.
 */
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export const PROJECT_AGENTS = new Set([
  "repository-scout",
  "standard-planner",
  "system-architect",
  "critical-architect",
  "fable-strategist",
  "fable-rescue",
  "routine-implementer",
  "sonnet-implementer",
  "complex-implementer",
  "standard-reviewer",
  "critical-reviewer",
]);

export const FABLE_AGENTS = new Set(["fable-strategist", "fable-rescue"]);

export const IMPLEMENTERS = new Set([
  "routine-implementer",
  "sonnet-implementer",
  "complex-implementer",
]);

export const FABLE_MODELS = new Set(["fable", "best"]);

// F3: `tool_input.model` and `tool_input.subagent_type` are compared
// case- and whitespace-insensitively — an unnormalized `"Best"`,
// `" best"`, or a dated Fable model id would otherwise slip past the
// Fable-model check, and a plugin-namespaced type like
// `some-plugin:fable-strategist` would slip past the Fable-role check.
// Over-blocking here is free: whether Claude Code's Agent tool would
// ever actually emit such a value is unknown, which is exactly the case
// for normalizing defensively.
function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

const FABLE_STRATEGIST_PATTERN = /(?:^|:)fable-strategist$/;
const FABLE_RESCUE_PATTERN = /(?:^|:)fable-rescue$/;

function isFableModel(normalizedModel) {
  return normalizedModel === "best" || normalizedModel.includes("fable");
}

function isFableRole(normalizedType) {
  return FABLE_STRATEGIST_PATTERN.test(normalizedType) || FABLE_RESCUE_PATTERN.test(normalizedType);
}

function isFableRescueRole(normalizedType) {
  return FABLE_RESCUE_PATTERN.test(normalizedType);
}

const IMPLEMENTATION_MARKERS = [
  /^\s*Editing allowed:\s*yes/im,
  /\bapply the (?:patch|diff|fix|changes)\b/i,
  /\bwrite the (?:code|implementation|files)\b/i,
  /\bedit the files?\b/i,
];

const SENTENCES = {
  "nested-delegation":
    "Only the main session delegates; return `STOP: discovery needed — …` to the orchestrator instead.",
  "model-override-non-fable": "That model is reserved for the Fable roles.",
  "evidence-missing": "A FABLE_ESCALATION evidence line is required for this role or model.",
  "evidence-malformed": "The FABLE_ESCALATION evidence line is not valid JSON.",
  "evidence-field": "The evidence is missing or invalid for field: {field}.",
  assignment: "The evidence's assignment field does not match this role.",
  "implementation-marker": "A Fable role cannot be given implementation work.",
  "internal-error": "An internal error occurred while evaluating the request.",
};

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function deny(code, field) {
  const sentence = (SENTENCES[code] ?? "That request is not permitted.").replace(
    "{field}",
    field ?? "unknown",
  );
  const payload = {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: `fable-gate: ${sentence} [code:${code}]`,
    },
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function extractEvidence(prompt) {
  if (typeof prompt !== "string") return { status: "missing" };
  const match = /^\s*FABLE_ESCALATION:\s*(\{.*\})\s*$/m.exec(prompt);
  if (!match) return { status: "missing" };
  try {
    const evidence = JSON.parse(match[1]);
    return { status: "ok", evidence };
  } catch {
    return { status: "malformed" };
  }
}

function validateEvidenceFields(evidence) {
  if (evidence.fable_escalation !== true) return "fable_escalation";
  if (
    typeof evidence.reason !== "string" ||
    evidence.reason.trim().length < 20
  ) {
    return "reason";
  }
  if (
    !Number.isInteger(evidence.score) ||
    evidence.score < 0 ||
    evidence.score > 27
  ) {
    return "score";
  }
  if (evidence.assignment !== "planning" && evidence.assignment !== "rescue") {
    return "assignment";
  }
  if (evidence.no_implementation !== true) return "no_implementation";
  const because =
    typeof evidence.opus_insufficient_because === "string" &&
    evidence.opus_insufficient_because.trim().length >= 20;
  const priorAttempts =
    Array.isArray(evidence.prior_attempts) &&
    evidence.prior_attempts.length >= 1 &&
    evidence.prior_attempts.every(
      (s) => typeof s === "string" && s.trim().length > 0,
    );
  if (!because && !priorAttempts) return "opus_insufficient_because";
  return null;
}

function hasImplementationMarker(prompt) {
  if (typeof prompt !== "string") return false;
  return IMPLEMENTATION_MARKERS.some((re) => re.test(prompt));
}

export function main() {
  const raw = readStdin();
  if (!raw) return;

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    return;
  }

  try {
    const callerType = normalize(payload?.agent_type);
    if (PROJECT_AGENTS.has(callerType)) {
      deny("nested-delegation");
      return;
    }

    const toolInput = payload?.tool_input ?? {};
    const model = normalize(toolInput.model);
    const type = normalize(toolInput.subagent_type);

    if (isFableModel(model) && !isFableRole(type)) {
      deny("model-override-non-fable");
      return;
    }

    if (!isFableRole(type) && !isFableModel(model)) return;

    const extracted = extractEvidence(toolInput.prompt);
    if (extracted.status === "missing") {
      deny("evidence-missing");
      return;
    }
    if (extracted.status === "malformed") {
      deny("evidence-malformed");
      return;
    }

    const evidence = extracted.evidence;
    const badField = validateEvidenceFields(evidence);
    if (badField) {
      deny("evidence-field", badField);
      return;
    }

    if (isFableRescueRole(type) && evidence.assignment !== "rescue") {
      deny("assignment");
      return;
    }

    if (hasImplementationMarker(toolInput.prompt)) {
      deny("implementation-marker");
      return;
    }
  } catch {
    deny("internal-error");
  }
}

const isMain =
  typeof process.argv[1] === "string" &&
  import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
