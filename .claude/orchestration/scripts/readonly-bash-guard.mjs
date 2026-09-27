#!/usr/bin/env node
/**
 * PreToolUse hook for the Bash tool. Restricts every read-only role
 * (`READ_ONLY_AGENTS`) to a small allowlist of read-only inspection
 * commands. The main session and the three implementers are untouched —
 * this hook only ever narrows what a read-only agent can run, never what
 * anyone else can.
 *
 * Stdin: the PreToolUse JSON payload. Stdout: nothing, or exactly one
 * deny object. Exit: always 0 (a hook error must never block a tool
 * call it was never meant to gate — see ~/.claude/orchestration/README.md,
 * "Known limits", for what that means and how to manually verify this
 * control after an upgrade).
 *
 * The guard never widens permissions: it only ever emits a deny object
 * or nothing. A bug here can make the guard over-restrictive, never
 * over-permissive.
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

const ALLOWED_NON_GIT_COMMANDS = new Set([
  "ls",
  "cat",
  "head",
  "tail",
  "wc",
  "grep",
  "rg",
  "pwd",
  "echo",
  "true",
  "false",
  "which",
  "file",
  "stat",
  "du",
  "tree",
]);

const GIT_SUBCOMMANDS = new Set([
  "diff",
  "log",
  "show",
  "status",
  "ls-files",
  "blame",
  "rev-parse",
  "grep",
  "describe",
  "branch",
]);

const BRANCH_ALLOWED_ARGS = new Set(["--list", "-a", "-r", "--show-current"]);

// -C reads any repo on disk, --textconv/--ext-diff run filters from
// gitattributes/config, the rest execute an external program. Consequence,
// documented: `git log -c` and `git diff -C` are also refused.
const GIT_REJECTED_OPTIONS = [
  "-c",
  "-C",
  "-O",
  "--config-env",
  "--exec-path",
  "--git-dir",
  "--work-tree",
  "--output",
  "--ext-diff",
  "--textconv",
  "--open-files-in-pager",
  "--pager",
  "--upload-pack",
  "--receive-pack",
];

const REJECTED_OPTIONS = {
  tail: ["-f", "-F", "--follow"],
  tree: ["-o"],
  rg: ["--pre", "--pre-glob", "--hostname-bin", "--search-zip", "-z"],
};

const DENIED_COMMANDS = new Set(
  `env command builtin time nice nohup timeout xargs eval exec source . sh
   bash zsh dash ksh fish node python python3 perl ruby npx pnpm npm yarn
   bun deno docker supabase curl wget sudo doas su rm mv cp ln mkdir rmdir
   touch chmod chown kill killall sed awk find tee dd truncate install
   patch make open osascript defaults launchctl crontab ssh scp rsync nc
   telnet psql tsx vitest next eslint tsc`
    .split(/\s+/)
    .filter(Boolean),
);

const SENTENCES = {
  "not-a-string": "The command must be a plain string.",
  redirection: "Redirection is not permitted.",
  substitution: "Command substitution is not permitted.",
  expansion: "Variable or brace expansion is not permitted.",
  continuation: "Line continuations are not permitted.",
  "control-char": "Control characters are not permitted.",
  empty: "No command was found to run.",
  "env-prefix": "Inline environment variable assignments are not permitted.",
  "path-qualified": "Path-qualified or relative binaries are not permitted.",
  "denied-command": "That command is not available to this role.",
  "not-allowlisted": "That command is not on the allowlist for this role.",
  "git-option": "That git option is not permitted.",
  "git-subcommand": "That git subcommand is not permitted.",
  "git-branch-arg":
    "Only git branch --list, -a, -r or --show-current are permitted.",
  option: "That option is not permitted for this command.",
  "internal-error": "An internal error occurred while evaluating the command.",
};

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function deny(code) {
  const sentence = SENTENCES[code] ?? "That command is not permitted.";
  const payload = {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason:
        `readonly-bash-guard: ${sentence} [code:${code}] This role may run ` +
        "only read-only inspection commands (git diff|log|show|status|" +
        "ls-files|blame|rev-parse|grep|describe|branch --list; ls cat head " +
        "tail wc grep rg pwd echo which file stat du tree) with no " +
        "redirection, substitution, expansion or wrapper. Ask the " +
        "orchestrator to run validation and paste the output.",
    },
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function hasBadControlChar(str) {
  for (let i = 0; i < str.length; i += 1) {
    const code = str.charCodeAt(i);
    if (code < 32 && code !== 9 && code !== 10 && code !== 13) return true;
  }
  return false;
}

// Shared by both the git and non-git per-command checks. A long option
// (`--follow`, `--config-env`, ...) matches by exact value or a `key=`
// prefix, unchanged. A single-dash single-letter option (`-f`, `-c`, ...)
// is rejected if its letter appears ANYWHERE in a combined short-option
// cluster (`-nf`, `-cC`, ...), not only when the token equals the option
// alone — `token.startsWith(option)` missed `tail -nf`, `tree -ao`,
// `git -cC`. Over-blocking an attached value that happens to contain the
// same letter (`git -ccore.pager=sh`) is accepted, not a designed match:
// the guard is quote- and getopt-unaware by design, and every ambiguity
// resolves to deny.
function matchesOption(token, option) {
  if (option.startsWith("--")) {
    return token === option || token.startsWith(`${option}=`);
  }
  if (!token.startsWith("-") || token.startsWith("--")) return false;
  const letter = option[1];
  return token.slice(1).includes(letter);
}

function evaluateGit(tokens) {
  const args = tokens.slice(1);
  for (const token of args) {
    for (const option of GIT_REJECTED_OPTIONS) {
      if (matchesOption(token, option)) return "git-option";
    }
  }
  const subIndex = args.findIndex((token) => !token.startsWith("-"));
  if (subIndex === -1) return "git-subcommand";
  const subcommand = args[subIndex];
  if (!GIT_SUBCOMMANDS.has(subcommand)) return "git-subcommand";
  if (subcommand === "branch") {
    const rest = args.slice(subIndex + 1);
    for (const arg of rest) {
      if (!BRANCH_ALLOWED_ARGS.has(arg)) return "git-branch-arg";
    }
  }
  return null;
}

function evaluateSegment(seg) {
  const tokens = seg.split(/\s+/).filter(Boolean);
  const head = tokens[0];
  if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(head)) return "env-prefix";
  if (head.includes("/")) return "path-qualified";
  if (DENIED_COMMANDS.has(head)) return "denied-command";
  if (head === "git") return evaluateGit(tokens);
  if (!ALLOWED_NON_GIT_COMMANDS.has(head)) return "not-allowlisted";
  const rejects = REJECTED_OPTIONS[head];
  if (rejects) {
    for (const token of tokens.slice(1)) {
      for (const option of rejects) {
        if (matchesOption(token, option)) return "option";
      }
    }
  }
  return null;
}

function evaluate(cmd) {
  if (/[<>]/.test(cmd)) return "redirection";
  if (cmd.includes("`") || cmd.includes("$(")) return "substitution";
  if (cmd.includes("${") || cmd.includes("$'") || /\$[A-Za-z_]/.test(cmd)) {
    return "expansion";
  }
  if (cmd.includes("\\\n")) return "continuation";
  if (hasBadControlChar(cmd)) return "control-char";

  const segments = cmd
    .split(/[;&|\n\r]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (segments.length === 0) return "empty";

  for (const seg of segments) {
    const code = evaluateSegment(seg);
    if (code) return code;
  }
  return null;
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
    const cmd = payload.tool_input?.command;
    if (typeof cmd !== "string") {
      deny("not-a-string");
      return;
    }
    const code = evaluate(cmd);
    if (code) deny(code);
  } catch {
    deny("internal-error");
  }
}

const isMain =
  typeof process.argv[1] === "string" &&
  import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
