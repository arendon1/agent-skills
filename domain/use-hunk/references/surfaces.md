# Surfaces — where hunk runs

Three surfaces, in priority order. The first that matches wins.

## Detection matrix

| Surface | Detect with | Confidence when |
|---|---|---|
| **cmux** | `command -v cmux && [ -n "$CMUX_*" ]` | cmux is installed AND the agent is inside a cmux-managed pane |
| **herdr** | `test "${HERDR_ENV:-}" = 1` | the agent is inside a herdr pane (herdr sets this env on its managed terminals) |
| **manual** | (fallback) | neither of the above |

Order of checks: **cmux first, then herdr, then manual.** Both cmux and
herdr can technically be present (one nested in the other, or the user
has both installed); cmux wins because it is the operator's primary
surface in this stack and exposes richer pane types.

## Surface 1 — cmux

cmux is the operator's primary terminal multiplexer. When the agent
detects cmux, it should:

1. Load the `use-cmux` skill transiently for the actual pane-open
   command. Do not inline `cmux` CLI calls in use-hunk.
2. Open a new cmux pane (split or workspace, depending on the change
   size — large diffs deserve their own workspace).
3. Run `hunk diff` (or `hunk show <ref>`) in that pane.
4. Wait for the cmux pane to register the hunk session with the broker.
5. Verify: `hunk session list --json` returns a session whose `repo`
   matches the current working directory.

Concrete pattern (delegated to `use-cmux`):

```text
# pseudocode — actual command in use-cmux skill
pane_id = cmux.split(direction="right", no_focus=true)
cmux.pane_run(pane_id, "hunk diff")  # or "hunk show HEAD~1"
# wait for broker registration
hunk_session = poll_until(lambda: hunk_session_list_has_repo(cwd),
                          timeout_ms=5000, interval_ms=250)
```

If the broker does not register within ~5s, fall back to surface 3
(manual) and print the literal command for the operator.

## Surface 2 — herdr

herdr is the portable multiplexer (Linux/macOS/Windows). When cmux is
not available but the agent is inside a herdr pane (`HERDR_ENV=1`):

1. Load the `use-herdr` skill transiently. Do not inline herdr CLI
   calls.
2. Open a new herdr pane with `pane split --direction right --no-focus`
   (or a fresh workspace for large diffs).
3. Run `hunk diff` in that pane.
4. Verify: `hunk session list --json`.

Concrete pattern (delegated to `use-herdr`):

```text
pane_id = herdr.pane_split(current=true, direction="right", no_focus=true)
herdr.pane_run(pane_id, "hunk diff")
hunk_session = herdr.pane_wait_output(pane_id, match="ready", timeout_ms=5000)
# then verify broker
hunk_session_list_has_repo(cwd)
```

If the broker does not register, fall back to manual.

## Surface 3 — manual

Neither cmux nor herdr is available. Print a literal command in chat
and wait.

```text
Listo. Cambios en 2 archivos (47+/12-).
- src/auth.ts:42-78 — extraje token rotation a un helper
- test/auth.test.ts:120-145 — cobertura del helper

Abre Hunk en otra terminal con:
  cd <absolute-path-to-repo> && hunk diff

Después escribe 'go' o feedback.
```

The agent MUST wait for the operator's next message; it MUST NOT
auto-resume on a timer. The operator's "I opened it" or "go" is the
signal.

## Failure handling

| Failure | Behavior |
|---|---|
| `command -v hunk` fails | fall back to `git diff` in chat; print install hint once per session: "Install: `brew install hunk`" |
| broker doesn't register (port 47657 silent) | print manual command as fallback; the operator can run hunk in any terminal |
| sandbox blocks `127.0.0.1:47657` (some agent sandboxes do) | print raw patch in chat: `hunk session review --repo . --include-patch --json`; ask "go?" |
| cmux pane opens but `hunk diff` errors | read pane output, surface the error in chat, ask the operator to run hunk manually |
| operator switches terminals mid-pause | broker re-resolves by `--repo <cwd>` on every input; agent re-verifies on the next message |

## Re-verification on every operator message

After a pause, the operator may type something hours later. The agent
MUST re-check the hunk session on the FIRST operator message after a
long gap (heuristic: > 2 minutes since the last verify):

```bash
hunk session list --json
```

If the session is gone (operator closed hunk, terminal restarted, etc.),
the agent re-prompts: "hunk session is no longer alive. Reopen with
`<command>` and confirm, or say 'go' to skip the review."

The agent never assumes the session is still up. Broker state is
verified, not remembered.
