#!/usr/bin/env node
/**
 * SubagentStart / SubagentStop hook. Appends one privacy-bounded JSONL
 * line recording that a delegation started or stopped — never what was
 * said or run inside it.
 *
 * Stdin: the SubagentStart or SubagentStop JSON payload. Stdout: nothing,
 * ever. Exit: always 0 — the whole body is one try/catch so a broken
 * logger can never block delegation.
 *
 * Closed key allowlist (top level): ts, event, project, sessionId, agentId,
 * agentType, requested, transcriptPath, status, durationMs. `requested`
 * is exactly model/effort/maxTurns. Nothing is ever copied from the
 * payload except these fields, explicitly by name — no spread, no
 * Object.assign.
 *
 * `agentType` normally comes from the payload's `agent_type`. A Claude
 * Code build older than 2.1.257 was observed emitting SubagentStop with
 * `agent_type: ""` (and no SubagentStart at all), which left every line
 * unattributable — the fail-open class CLAUDE.md warns about. When
 * `agent_type` is absent or empty we therefore recover the role from the
 * harness's own sibling `agent-<agentId>.meta.json`, reading that file's
 * `agentType` field and NOTHING else (it also holds `description`,
 * `toolUseId`, `spawnDepth` and `requestShape`, none of which are ever
 * copied). The fallback cannot invent a role: an internal subagent that
 * writes no meta file still logs an empty `agentType`.
 */
import {
  appendFileSync,
  closeSync,
  mkdirSync,
  openSync,
  readFileSync,
  readSync,
  renameSync,
  statSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const LIFECYCLE_KEYS = [
  "ts",
  "event",
  "project",
  "sessionId",
  "agentId",
  "agentType",
  "requested",
  "transcriptPath",
  "status",
  "durationMs",
];

export const REQUESTED_KEYS = ["model", "effort", "maxTurns"];

const MAX_BYTES = 1024 * 1024;
const MAX_TAIL_BYTES = 512 * 1024;

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function projectDir() {
  return process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
}

// Global install: one log for every project on this machine, so each line
// also carries the project's directory name. Overridable for tests.
function runtimeDir() {
  return (
    process.env.CLAUDE_ORCH_RUNTIME_DIR ??
    path.join(os.homedir(), ".claude", "orchestration", "runtime")
  );
}

// A project agent file shadows the global one of the same name, exactly as
// Claude Code resolves them, so the requested config is read in that order.
function readRequested(agentType) {
  if (typeof agentType !== "string" || !/^[a-z0-9-]+$/.test(agentType)) {
    return undefined;
  }
  let source;
  for (const base of [path.join(projectDir(), ".claude"), path.join(os.homedir(), ".claude")]) {
    try {
      source = readFileSync(path.join(base, "agents", `${agentType}.md`), "utf8");
      break;
    } catch {
      // not defined at this level; try the next one
    }
  }
  if (source === undefined) return undefined;
  const frontmatterMatch = /^---\n([\s\S]*?)\n---/.exec(source);
  if (!frontmatterMatch) return undefined;
  const block = frontmatterMatch[1];
  const requested = {};
  for (const key of REQUESTED_KEYS) {
    const re = new RegExp(`^${key}:\\s*(.+)$`, "m");
    const match = re.exec(block);
    if (!match) continue;
    const value = match[1].trim();
    requested[key] = key === "maxTurns" ? Number(value) : value;
  }
  return Object.keys(requested).length > 0 ? requested : undefined;
}

/** Reads at most the last `maxBytes` of `file`. If the read starts
 *  mid-file, the (possibly truncated) first line fragment is dropped so
 *  every remaining line is whole. Any failure returns "". */
function readTail(file, maxBytes) {
  let fd;
  try {
    const stats = statSync(file);
    const start = Math.max(0, stats.size - maxBytes);
    const length = stats.size - start;
    if (length <= 0) return "";
    fd = openSync(file, "r");
    const buffer = Buffer.alloc(length);
    readSync(fd, buffer, 0, length, start);
    let text = buffer.toString("utf8");
    if (start > 0) {
      const firstNewline = text.indexOf("\n");
      text = firstNewline === -1 ? "" : text.slice(firstNewline + 1);
    }
    return text;
  } catch {
    return "";
  } finally {
    if (fd !== undefined) {
      try {
        closeSync(fd);
      } catch {
        // already closed or never opened
      }
    }
  }
}

/** The SubagentStart that OPENED the run now stopping: the first Start
 *  for this agentId since that agentId last stopped, or undefined.
 *
 *  SubagentStart fires again every time an agent is resumed — a
 *  SendMessage to a still-open delegation emits a second, third, fourth
 *  Start with the same agentId and no Stop in between (observed: one
 *  implementer Started four times and never Stopped at all). Taking the
 *  LAST such Start, as this did until 2026-09-21, measured only the final
 *  resumed leg: a `critical-architect` that ran 3m54s reported 1m42s, and
 *  a 20m34s implementer run reported 2m22s. Taking the FIRST Start of the
 *  segment reports the delegation's wall clock instead, which is what the
 *  §10 execution report means by how long it took. That wall clock does
 *  include the orchestrator's own thinking time between resumes; it is an
 *  elapsed time, not a measure of the agent's compute.
 *
 *  Resetting on a Stop is what keeps an agentId's earlier, completed run
 *  from leaking into its next one. For the ordinary single-Start
 *  delegation this is identical to the old behaviour.
 *
 *  Reading happens before this Stop's own line is appended, and before
 *  any rotation, so a Start near the rotation boundary is never missed by
 *  acting on a stale file. A segment whose opening Start has already
 *  scrolled out of the tail window falls back to the earliest Start still
 *  visible, which under-reports exactly as the old logic did — never
 *  over-reports. */
function findMatchingStart(agentId) {
  if (typeof agentId !== "string" || !agentId) return undefined;
  const file = path.join(runtimeDir(), "lifecycle.jsonl");
  const tail = readTail(file, MAX_TAIL_BYTES);
  if (!tail) return undefined;
  let found;
  for (const line of tail.split("\n")) {
    if (!line) continue;
    let obj;
    try {
      obj = JSON.parse(line);
    } catch {
      continue;
    }
    if (obj?.agentId !== agentId) continue;
    if (obj?.event === "SubagentStop") {
      // That run is closed; anything after this opens a new one.
      found = undefined;
    } else if (obj?.event === "SubagentStart" && found === undefined) {
      found = obj;
    }
  }
  return found;
}

/** Non-negative integer milliseconds since the matching Start's `ts`, or
 *  undefined on any failure (no match, malformed ts, negative delta). */
function computeDurationMs(agentId) {
  try {
    const start = findMatchingStart(agentId);
    if (!start) return undefined;
    const startMs = Date.parse(start.ts);
    if (Number.isNaN(startMs)) return undefined;
    const duration = Date.now() - startMs;
    return duration >= 0 ? duration : undefined;
  } catch {
    return undefined;
  }
}

function rotateIfLarge(file) {
  try {
    const stats = statSync(file);
    if (stats.size > MAX_BYTES) {
      renameSync(file, `${file}.1`);
    }
  } catch {
    // Missing file, or a race with another rotation — nothing to rotate.
  }
}

/** A role slug is a short, self-contained token. Anything else — a
 *  path separator, "..", whitespace, an over-long value — is rejected,
 *  because this value is read off disk and then used to build a file
 *  path in `readRequested`. This is the FIRST of two gates, and
 *  deliberately the looser one: it also accepts the uppercase built-in
 *  role names (`Explore`, `Plan`) so those are still logged.
 *  `readRequested` applies its own stricter `^[a-z0-9-]+$` before it
 *  joins the value into a path, and that remains the gate on the path
 *  build. */
function isRoleSlug(value) {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);
}

/** The harness writes `<transcript>.meta.json` beside each subagent
 *  transcript, holding the role that was requested. Stop payloads carry
 *  `agent_transcript_path` directly; Start payloads carry only the
 *  session `transcript_path`, whose subagents live in a directory named
 *  after it. Returns undefined on any failure — a missing, unreadable,
 *  malformed or implausible file is simply no answer. */
function readAgentTypeFromMeta(payload) {
  try {
    const agentId = payload?.agent_id;
    let metaFile;
    const stopPath = payload?.agent_transcript_path;
    if (typeof stopPath === "string" && stopPath.endsWith(".jsonl")) {
      metaFile = `${stopPath.slice(0, -".jsonl".length)}.meta.json`;
    } else {
      const sessionPath = payload?.transcript_path;
      if (
        typeof sessionPath !== "string" ||
        !sessionPath.endsWith(".jsonl") ||
        !isRoleSlug(agentId)
      ) {
        return undefined;
      }
      const sessionDir = sessionPath.slice(0, -".jsonl".length);
      metaFile = path.join(sessionDir, "subagents", `agent-${agentId}.meta.json`);
    }
    const meta = JSON.parse(readFileSync(metaFile, "utf8"));
    // Only this one field is ever read. `description` and everything
    // else in the file stay out of the log.
    return isRoleSlug(meta?.agentType) ? meta.agentType : undefined;
  } catch {
    return undefined;
  }
}

export function buildEntry(payload) {
  const event = payload?.hook_event_name;
  const payloadType = payload?.agent_type;
  // The payload is authoritative when it says anything at all; the meta
  // file only fills a gap it left.
  const agentType =
    typeof payloadType === "string" && payloadType !== ""
      ? payloadType
      : (readAgentTypeFromMeta(payload) ?? payloadType);
  const entry = {
    ts: new Date().toISOString(),
    event,
    project: path.basename(projectDir()),
    sessionId: payload?.session_id,
    agentId: payload?.agent_id,
    agentType,
    status: event === "SubagentStop" ? "stopped" : "started",
  };
  const requested = readRequested(agentType);
  if (requested) entry.requested = requested;
  if (event === "SubagentStop") {
    if (typeof payload?.agent_transcript_path === "string") {
      entry.transcriptPath = payload.agent_transcript_path;
    }
    // Read the existing log BEFORE this line is appended and before any
    // rotation, so a Start near the end of the file is never missed.
    const durationMs = computeDurationMs(payload?.agent_id);
    if (durationMs !== undefined) entry.durationMs = durationMs;
  }
  return entry;
}

/** True for the main session's own turn ending, which Claude Code 2.1.257
 *  reports through the SubagentStop hook even though no subagent is
 *  involved.
 *
 *  Identified 2026-09-21 by correlating this session's log against its
 *  transcript: 3 `stop_hook_summary` entries, 3 such lines, a clean 1:1
 *  pairing 1.3-2.2s after each turn end. They carry no `agent_type` (the
 *  main session has no role), never a preceding SubagentStart, and an
 *  `agent_transcript_path` naming a subagent transcript that does not
 *  exist. In `epic-lederberg` they looked like they trailed each
 *  delegation by 7-10s; that was incidental — launching a BACKGROUND
 *  agent returns at once and so ends the turn.
 *
 *  They are dropped because this is a delegation log: one line per turn
 *  is pure noise, it cannot be attributed to any role, and at roughly a
 *  line per turn it would drive rotation and scroll real Start lines out
 *  of the correlation window, silently breaking `durationMs`.
 *
 *  A real delegation is not at risk of being dropped here: it has to lose
 *  BOTH its `agent_type` and its meta file, and the pre-2.1.257 payloads
 *  that lost `agent_type` still wrote meta files, so the fallback keeps
 *  them. Only SubagentStop is filtered — a Start with no role has never
 *  been observed, and would be an anomaly worth seeing in the log. */
function isMainSessionTurnEnd(entry) {
  return (
    entry.event === "SubagentStop" &&
    (entry.agentType === undefined || entry.agentType === "")
  );
}

export function main() {
  try {
    const raw = readStdin();
    if (!raw) return;

    let payload;
    try {
      payload = JSON.parse(raw);
    } catch {
      return;
    }

    const entry = buildEntry(payload);
    if (isMainSessionTurnEnd(entry)) return;
    const dir = runtimeDir();
    mkdirSync(dir, { recursive: true });
    const file = path.join(dir, "lifecycle.jsonl");
    rotateIfLarge(file);
    appendFileSync(file, `${JSON.stringify(entry)}\n`);
  } catch {
    // Never block delegation on a logging failure.
  }
}

const isMain =
  typeof process.argv[1] === "string" &&
  import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
