// agent-skills pi adapter (Layer 4).
//
// The ONLY place harness-specific coupling lives. Skills express behavior; this
// adapter maps behavior to pi's tools. It does three things:
//   1. resources_discover — register the repo root as a skills directory
//      (every skill lives in its own dir at the repo root, per AGENTS.md §2).
//   2. session_start / session_compact — flag that the bootstrap skill should be
//      (re-)injected. bootstrap is the only bootstrap-invoked skill (§4).
//   3. context — inject the bootstrap skill body + the pi tool mapping at the
//      top of the conversation, unless already present.
//
// Modeled on superpowers/.pi/extensions/superpowers.ts. Adapted for agent-skills:
// skills at the repo root in category buckets (process/ domain/ utility/),
// bootstrap/SKILL.md (in the utility/ bucket) as injection.

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const BOOTSTRAP_MARKER = "agent-skills:bootstrap injection for pi";

const extensionDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = resolve(extensionDir, "../..");
// Skills live in category buckets: <layer>/<skill>/ (AGENTS.md §2).
const skillsDir = packageRoot;
// bootstrap lives in the utility/ bucket (invocation: bootstrap). Search known
// buckets so the adapter survives a future reorg; fall back to repo root.
const bootstrapSkillPath = [
  resolve(skillsDir, "utility", "bootstrap", "SKILL.md"),
  resolve(skillsDir, "process", "bootstrap", "SKILL.md"),
  resolve(skillsDir, "domain", "bootstrap", "SKILL.md"),
  resolve(skillsDir, "bootstrap", "SKILL.md"),
].find((p) => existsSync(p)) ?? resolve(skillsDir, "utility", "bootstrap", "SKILL.md");

let cachedBootstrap: string | null | undefined;

export default function agentSkillsPiExtension(pi: ExtensionAPI) {
  let injectBootstrap = true;

  // Register the repo root for skill discovery. pi scans for subdirs with SKILL.md.
  pi.on("resources_discover", async () => ({
    skillPaths: [skillsDir],
  }));

  // Re-inject bootstrap at session start and after every compaction.
  pi.on("session_start", async () => {
    injectBootstrap = true;
  });

  pi.on("session_compact", async () => {
    injectBootstrap = true;
  });

  // Stop injecting once the agent has finished responding (avoids re-injecting
  // mid-turn in some harness flows).
  pi.on("agent_end", async () => {
    injectBootstrap = false;
  });

  // Inject the bootstrap skill at the top of the conversation (after any
  // compaction summaries), unless it is already present.
  pi.on("context", async (event) => {
    if (!injectBootstrap) return;
    if (event.messages.some(messageContainsBootstrap)) return;

    const bootstrap = getBootstrapContent();
    if (!bootstrap) return;

    const bootstrapMessage = {
      role: "user" as const,
      content: [{ type: "text" as const, text: bootstrap }],
      timestamp: Date.now(),
    };

    const insertAt = firstNonCompactionSummaryIndex(event.messages);
    return {
      messages: [
        ...event.messages.slice(0, insertAt),
        bootstrapMessage,
        ...event.messages.slice(insertAt),
      ],
    };
  });
}

function getBootstrapContent(): string | null {
  if (cachedBootstrap !== undefined) return cachedBootstrap;

  try {
    const skillContent = readFileSync(bootstrapSkillPath, "utf8");
    const body = stripFrontmatter(skillContent);
    cachedBootstrap = `${BOOTSTRAP_MARKER}

You have agent-skills.

The bootstrap skill content is included below and is already loaded for this pi session. Follow it now. Do not try to load bootstrap again — it is active.

${body}

${piToolMapping()}`;
    return cachedBootstrap;
  } catch {
    cachedBootstrap = null;
    return null;
  }
}

function stripFrontmatter(content: string): string {
  const match = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)$/);
  return (match ? match[1] : content).trim();
}

// The behavior -> tool mapping. This is the ONLY place pi-specific tool names
// appear; skills themselves never name them (AGENTS.md §9 agnosticism).
function piToolMapping(): string {
  return `## pi tool mapping

agent-skills express behavior in harness-agnostic terms. This adapter maps those
behaviors to pi's concrete tools for this session.

**Load a skill:** pi has native skills. When a skill says to "load a skill" or
"invoke the X skill", either let pi's native skill system resolve it, or read the
relevant \`SKILL.md\` with the \`read\` tool. Do not invent a separate "Skill" tool.

**Dispatch a subagent:** pi does not ship a standard subagent tool. If a
\`subagent\` tool is available (e.g. from a subagents extension), use it for
subagent workflows (the dispatch skill). Otherwise do the work in this session or
explain the missing capability instead of inventing task-tool calls.

**Track a task:** if an installed todo/task tool is available, use it. Otherwise
track work in the active plan's PLAN.md task status cells (build flips
\`[ ]\` -> \`~\` -> \`[x]\`) or a repo-local TODO.md.

**Built-in coding tools:** pi's built-in tools are lowercase: \`read\`, \`write\`,
\`edit\`, \`bash\`, plus optional \`grep\`, \`find\`, and \`ls\`. Use those for the
corresponding actions: read a file, create or edit files, run shell commands,
search file contents, find files by name, list directories.

**Recall long-term memory:** memory substrate is out of scope for agent-skills.
Skills degrade gracefully to file-only (the plan artifacts in docs/plans/ and
CONTEXT.md at the repo root are the externalized state the agent maintains).`;
}

function messageContainsBootstrap(message: unknown): boolean {
  const content = (message as { content?: unknown }).content;
  if (typeof content === "string") return content.includes(BOOTSTRAP_MARKER);
  if (!Array.isArray(content)) return false;
  return content.some((part) => {
    return (
      part &&
      typeof part === "object" &&
      (part as { type?: unknown }).type === "text" &&
      typeof (part as { text?: unknown }).text === "string" &&
      (part as { text: string }).text.includes(BOOTSTRAP_MARKER)
    );
  });
}

function firstNonCompactionSummaryIndex(messages: unknown[]): number {
  let index = 0;
  while ((messages[index] as { role?: unknown } | undefined)?.role === "compactionSummary") {
    index += 1;
  }
  return index;
}
