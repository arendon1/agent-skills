# Workflows — full worked examples with pitfalls

The `SKILL.md` sketches workflows A–E. This file is the long version: exact
command sequences, wait-vs-poll guidance, and the failure modes that bite.

## Workflow A — run a dev server in a dedicated pane

### Full sequence

```bash
# 0. Gate on herdr + HERDR_ENV.
command -v herdr >/dev/null 2>&1 || { echo "no herdr"; exit 1; }
test "${HERDR_ENV:-}" = 1 || { echo "not inside herdr"; exit 1; }

# 1. Create an isolated workspace (also creates first tab + root pane).
#    Parse the workspace ID and root pane ID from JSON.
RESP=$(herdr --json workspace create --cwd ~/projects/myapp --label "dev-server" --no-focus)
WS=$(echo "$RESP" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["workspace"]["workspace_id"])')
PANE=$(echo "$RESP" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["root_pane"]["pane_id"])')

# 2. Start the server. `pane run` sends text + Enter atomically.
herdr pane run "$PANE" "npm run dev"

# 3. Wait for the ready line — event-driven, no polling loop.
herdr pane wait-output "$PANE" --match "Local:" --source recent-unwrapped --timeout 30000

# 4. Read the tail to grab the port.
OUT=$(herdr pane read "$PANE" --source recent-unwrapped --lines 20)
PORT=$(echo "$OUT" | grep -oE "localhost:[0-9]+" | head -1 | cut -d: -f2)
echo "server up on :$PORT"

# 5. Watch logs on demand.
herdr pane read "$PANE" --source recent --lines 200

# 6. Stop and clean up.
herdr pane send-keys "$PANE" ctrl+c
herdr workspace close "$WS"
```

### Pitfalls

1. **`workspace create` returns three IDs.** `.result.workspace.workspace_id`,
   `.result.tab.tab_id`, `.result.root_pane.pane_id`. Capture the root pane ID
   — it's what you `pane run` into. If you only capture the workspace ID,
   recover the root pane with `herdr workspace get "$WS"`.

2. **`pane run` is atomic text + Enter.** Use it for commands. `pane
   send-text` sends text without Enter (useful to pre-fill a command for the
   human to review). `pane send-keys` sends key events (`enter`, `ctrl+c`, …).

3. **`pane wait-output` is the no-poll wait.** `--match <text>` or
   `--regex <pat>`, `--source recent-unwrapped` (best for logs — no soft
   wrapping), `--timeout MS`. It blocks until the text appears or timeout. This
   beats a sleep loop: no missed transitions, no wasted cycles.

4. **`pane read` sources matter.** `visible` = current viewport. `recent` =
   scrollback with wrapping. `recent-unwrapped` = no soft wrapping (best for
   grep/log parsing). `detection` = bottom-buffer snapshot used by agent
   detection. For "did the server print its port" use `recent-unwrapped --lines 30`.

5. **`pane send-keys ctrl+c` sends to the foreground process group.** If the
   shell is at a prompt, it clears the line — harmless. Always `pane read`
   first to know what state the pane is in.

6. **Don't lose the ID.** If you didn't capture `PANE` from `workspace create`,
   recover it: `herdr pane list --workspace "$WS"` (match by label if set) or
   `herdr workspace get "$WS"`.

### Servers that need env vars

```bash
herdr workspace create --cwd ~/projects/api --label "api" \
  --env DATABASE_URL="postgres://localhost/dev" --env PORT=8080 --no-focus
# or set env on the pane split:
herdr pane split --current --direction right --env DATABASE_URL="postgres://localhost/dev" --no-focus
```

herdr injects `HERDR_SOCKET_PATH`, `HERDR_ENV=1`, `HERDR_WORKSPACE_ID`,
`HERDR_TAB_ID`, `HERDR_PANE_ID` into every pane process. Reserved `HERDR_*`
variables cannot be overridden.

## Workflow B — open a localhost webapp

herdr has no built-in browser surface. Open the URL in the host browser:

```bash
# macOS
herdr pane run "$PANE" "open http://localhost:5173"
# Linux
herdr pane run "$PANE" "xdg-open http://localhost:5173"
# Windows (cmd)
herdr pane run "$PANE" "start http://localhost:5173"
```

For automated verification, run a smoke test in a dedicated pane:

```bash
TEST_PANE=$(herdr --json pane split --current --direction down --no-focus \
            | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$TEST_PANE" "curl -sS http://localhost:5173 | head -20"
herdr pane wait-output "$TEST_PANE" --regex "(<!DOCTYPE|<html|error)" \
      --source recent-unwrapped --timeout 10000
herdr pane read "$TEST_PANE" --source recent-unwrapped --lines 30
```

For full browser automation (DOM, screenshots), run a Playwright/Puppeteer
script in a pane or defer to a browser-automation capability.

## Workflow C — parallel work in its own pane

```bash
# 1. Split the current pane. Geometry: wide -> right, tall -> down.
P2=$(herdr --json pane split --current --direction right --no-focus \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')

# 2. Run the parallel command.
herdr pane run "$P2" "npm test 2>&1 | tee /tmp/test.log"

# 3. Wait for the result line (event-driven, no polling).
herdr pane wait-output "$P2" --regex "(passed|failed|[0-9]+ tests)" \
      --source recent-unwrapped --timeout 120000

# 4. Read the full result.
herdr pane read "$P2" --source recent-unwrapped --lines 200

# 5. Move to a new tab/workspace when it outgrows a split.
herdr pane move "$P2" --new-tab --label "tests" --no-focus
```

### Pitfalls

1. **`pane split` returns the new pane ID.** Always capture it. If you `pane
   run` into the old pane ID, you type into your own pane.

2. **`pane run` sends text + Enter.** `pane send-text` does not. Use `pane
   run` to execute, `pane send-text` to pre-fill.

3. **`pane wait-output` detects completion by text, not by "output stopped
   changing".** A long pause may be legitimate work. Match a known result
   line (`--regex "(passed|failed|...)"`) for reliable completion detection.

4. **For fully isolated parallel work, use a new workspace** (Workflow A) or a
   git worktree (Workflow E). A split shares the workspace's context; a
   workspace is isolated.

## Workflow D — launch a peer agent in its own pane

### Full sequence

```bash
# 1. Split a pane for the peer agent. Must be an available shell (no foreground
#    command/editor/agent running).
PANE=$(herdr --json pane split --current --direction right --no-focus \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')

# 2. Start the agent. --kind selects the CLI; returns after agent is ready.
herdr agent start reviewer --kind codex --pane "$PANE"

# 3. Prompt the agent and wait for it to settle (atomic submit + wait).
herdr agent prompt reviewer "Review the auth module in src/auth/" --wait --timeout 300000

# 4. Read its output.
herdr agent read reviewer --source recent-unwrapped --lines 200

# 5. Or wait on its state without reading (event-driven).
herdr agent wait reviewer --until done --timeout 600000

# 6. Focus its pane when the human needs to see it.
herdr agent focus reviewer

# 7. Rename for clarity if you start more agents.
herdr agent rename reviewer "auth-reviewer"
```

### Pitfalls

1. **`agent start` requires an available shell pane.** The pane must have a
   shell in the foreground — no running command, editor, or agent. Split a
   fresh pane or wait until one is idle.

2. **`agent prompt --wait` is atomic.** It submits text + Enter and waits for
   the first settled state (idle/done/blocked) in one call — no submit-then-
   poll race. Add `--until` for specific-state workflows
   (`--until done --until blocked`). Stalled detection returns
   `agent_prompt_stalled` after 5s.

3. **`agent wait` is server-owned and event-driven.** It pins the resolved
   pane occupant so a replacement cannot satisfy the wait. Use it to block
   until a peer reaches a state without reading output in a loop.

4. **Agent names must be unique.** `[a-z][a-z0-9_-]{0,31}`, unique among live
   agents. If you start a second agent of the same kind, give it a different
   name (`auth-reviewer`, `test-reviewer`, …).

5. **Alternate-screen caveat.** Some TUI-based agents use an alternate-screen
   buffer. If `agent read --lines N` returns no additional text, ask the agent
   to write its output to a temp file and read that file instead.

6. **Don't auto-approve on a peer's behalf.** If a peer agent becomes
   `blocked` (needs input/approval), surface it to the human via
   `herdr notification show` and let the human decide.

## Workflow E — git worktree as a workspace

```bash
# Create a worktree on a new branch and open it as a workspace.
herdr worktree create --cwd ~/projects/myapp --branch fix/auth --label "auth-fix" --focus

# List worktrees grouped by parent repo.
herdr worktree list --cwd ~/projects/myapp --json

# Open an existing worktree as a workspace.
herdr worktree open --cwd ~/projects/myapp --path ~/projects/myapp-worktrees/fix-auth

# Remove a worktree workspace (and the git worktree).
herdr worktree remove --workspace w2 --force
```

### Pitfalls

1. **Checkouts go under `[worktrees].directory`.** Configured in `config.toml`.
   Default is a sensible location; check with `herdr --default-config | grep -A2 worktrees`.

2. **`worktree create` creates a `git worktree` AND a herdr workspace.** The
   workspace is grouped with the parent repo in the sidebar. Removing the
   workspace removes the git worktree too (use `--force` if uncommitted changes).

3. **`--branch` creates a new branch; `--path` opens an existing worktree.**
   Use `--branch <name>` for new branch work, `--path <dir>` to reattach an
   existing worktree.

## Cross-workflow: coordination with agent state

```bash
# Roll up all agent states across workspaces.
herdr agent list

# Wait for a specific agent to finish, then read its output.
herdr agent wait reviewer --until done --timeout 600000
herdr agent read reviewer --source recent-unwrapped --lines 200

# Wait for multiple agents in sequence.
for AGENT in auth-reviewer test-reviewer docs-reviewer; do
  herdr agent wait "$AGENT" --until done --timeout 600000
  echo "=== $AGENT done ==="
  herdr agent read "$AGENT" --source recent-unwrapped --lines 50
done

# Notify the human when all agents are done.
herdr notification show "All reviewers done" --body "3/3 agents finished" --sound done

# Explain an agent's state for debugging.
herdr agent explain reviewer --json
```
