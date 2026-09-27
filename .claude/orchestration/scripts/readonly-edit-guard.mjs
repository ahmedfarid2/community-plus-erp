#!/usr/bin/env node
/**
 * PreToolUse hook for the Edit / Write / MultiEdit / NotebookEdit tools.
 * Defense in depth for the eight read-only agents: the `tools` /
 * `disallowedTools` frontmatter on each agent file is the primary,
 * authoritative control (Claude Code never offers these tools to those
 * agents in the first place); this hook only guards against a future
 * frontmatter edit that accidentally removes the restriction.
 *
 * Stdin: the PreToolUse JSON payload. Stdout: nothing, or exactly one
 * deny object. Exit: always 0.
 *
 * `READ_ONLY_AGENTS` is intentionally duplicated from
 * `readonly-bash-guard.mjs` rather than imported (each hook script is a
 * standalone process with no shared module state); a drift test proves
 * the two exported sets stay equal.
 */
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export const READ_ONLY_AGENTS = new Set([
  "repository-scout",
  "standard-planner",
  "system-architect",
  "critical-architect",
  "fable-strategist",
  "fable-rescue",
  "standard-reviewer",
  "critical-reviewer",
]);

const REASON =
  "readonly-edit-guard: this role is read-only and has no editing tool; " +
  "the tools/disallowedTools frontmatter is the primary control, this " +
  "hook is defense in depth. [code:readonly-edit] Return " +
  "`STOP: decision needed — <the question>` to the orchestrator instead.";

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function deny() {
  const payload = {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: REASON,
    },
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
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
  if (typeof payload?.agent_type !== "string") return;
  if (!READ_ONLY_AGENTS.has(payload.agent_type)) return;

  try {
    deny();
  } catch {
    // The reason string is static; nothing here can throw in practice,
    // but stay fail-silent rather than ever risk blocking a tool call
    // this hook was never meant to gate.
  }
}

const isMain =
  typeof process.argv[1] === "string" &&
  import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
