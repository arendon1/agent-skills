# Workflows — worked sequences

Long-form, copy-pasteable patterns. For command tables see
`commands.md`; for the mental model and pitfalls see the main `SKILL.md`.

## Workflow A — one-shot Gemini review of a diff (the canonical use)

Use when: you want a free Gemini-family second opinion on a diff under
review, without leaving the host harness.

```bash
# 1. Materialize the diff to review
REPO=~/projects/myapp
BASE=main
git -C "$REPO" diff "$BASE"..HEAD > /tmp/review-diff.txt

# 2. Hand it to agy with a cheap-but-strong Gemini model
agy -p "Review the diff in /tmp/review-diff.txt. Output three sections:
BLOCKING (must-fix), NON-BLOCKING (suggestions), FOLLOW-UPS (out of scope
but worth tracking). Be terse. Cite file:line for every issue." \
    --model "gemini-3.1-pro-high" \
    --add-dir "$REPO" \
    --print-timeout 5m
```

**Why this works:** `gemini-3.1-pro-high` is free under Google AI Pro;
`--add-dir` gives `agy` access to the full repo for context; 5m
timeout is enough for a single-pass review of a 500-line diff.

**Verify:** paste the output into the plan folder's `RESEARCH.md` so the
cross-check is part of the audit trail.

## Workflow B — Claude second-opinion on a plan

Use when: another agent (Pi, codex, etc.) wrote a plan, and you want a
Claude-family sanity check before merging.

```bash
REPO=~/projects/myapp
PLAN="$REPO/docs/plans/2026-07-29-feature-x/PLAN.md"

agy -p "Read $PLAN. Output: (1) hidden assumptions the plan makes about
runtime/dependencies, (2) failure modes not addressed, (3) missing
acceptance criteria. Be terse. Cite plan section numbers." \
    --model "claude-sonnet-4-6" \
    --add-dir "$REPO" \
    --print-timeout 5m
```

**Cost note:** `claude-sonnet-4-6` is billed per Google terms — not
subscription-free. Check whether the user wants this spend before
running.

**Save output** to `RESEARCH.md` alongside the plan.

## Workflow C — parallel batch (worktree fan-out)

Use when: N independent tasks that can run in isolated worktrees
(separate file scopes, no shared state).

```bash
REPO=~/projects/myapp
TASKS=(auth-refactor docs-update cleanup-dead-code)
PROMPTS_DIR=~/.cache/agy-prompts
mkdir -p "$PROMPTS_DIR"

# Write one prompt file per task
cat > "$PROMPTS_DIR/auth-refactor.txt" <<'EOF'
Refactor src/auth/ to use the new token validation contract in
docs/specs/auth-v2.md. Update tests. Run the auth suite.
EOF
cat > "$PROMPTS_DIR/docs-update.txt" <<'EOF'
Update README.md to reflect the new auth flow. Add a "Migrating from v1"
section.
EOF
cat > "$PROMPTS_DIR/cleanup-dead-code.txt" <<'EOF'
Find and remove dead code flagged in NOTES.md under "deprecated".
Run the test suite after each removal.
EOF

# Fan out — one worktree + one agy per task
cd "$REPO"
for task in "${TASKS[@]}"; do
  git worktree add "../wt-$task" -b "fix/$task"
  (
    cd "../wt-$task"
    agy -p "$(cat "$PROMPTS_DIR/$task.txt")" \
        --model "gemini-3.6-flash-high" \
        --dangerously-skip-permissions \
        --print-timeout 15m \
        > "/tmp/agy-$task.out" 2>&1
  ) &
done
wait

# Collect results
for task in "${TASKS[@]}"; do
  echo "=== $task ==="
  cat "/tmp/agy-$task.out"
done
```

**Bound concurrency to 2–3** unless the machine has headroom; `agy` is
heavier than `codex`. Use `wait` to gate the next phase on all
completions.

**Verify per worktree:** `git -C ../wt-$task diff main..HEAD` — a clean
diff + passing tests is the success signal. Don't trust stdout alone.

## Workflow D — interactive multi-turn under tmux

Use when: the user wants to drive `agy` interactively (exploratory
coding, slash commands, conversation resume) while the host harness watches.

```bash
# Start a named tmux session
tmux new-session -d -s agy -c ~/projects/myapp 'agy -i'
tmux send-keys -t agy 'Read README.md and propose three refactors' Enter

# Poll the pane
tmux capture-pane -t agy -p | tail -40

# Send a follow-up
tmux send-keys -t agy 'Focus on the auth module first' Enter

# Resume the most recent conversation in a new session
tmux new-session -d -s agy2 -c ~/projects/myapp 'agy -c'
```

**Resume from outside tmux:** `agy --conversation <id>` where `<id>` is
the conversation ID from `~/.gemini/antigravity-cli/conversations/`.

For herdr/cmux equivalents, see the `use-herdr` / `use-cmux` skills
(Workflow D in each).

## Workflow E — log triage when something fails

Use when: an `agy -p` run returned weird output, exited non-zero, or
the result doesn't match expectations.

```bash
LOG=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)

# 1. Confirm the run actually started
grep -E "Print mode: starting|initialized server successfully" "$LOG" | tail -5

# 2. Look for auth errors first (most common cause)
grep -E "not logged into|Auth succeeded|error getting token source" "$LOG" | tail -10

# 3. Look for model resolution errors
grep -E "Model ID .* not in local config|Model resolved" "$LOG" | tail -5

# 4. Look for permission denials
grep -E "permission|denied|allowNonWorkspaceAccess" "$LOG" | tail -10

# 5. Tail errors
grep "^E" "$LOG" | tail -30

# 6. Read the last 100 lines for the full picture
tail -100 "$LOG"
```

**Common diagnoses:**

| Log pattern | Cause | Fix |
|-------------|-------|-----|
| `You are not logged into Antigravity` followed by `silent auth succeeded` | Transient race — initial cache refresh lost a race with the keyring | Non-fatal; the run still completes. Ignore if `status: SUCCESS` |
| `You are not logged into Antigravity` repeating, no `silent auth succeeded` after | Empty keyring | Run `agy -i` once to trigger browser OAuth |
| `Model ID <x> not in local config` | Typo in `--model` | Run `agy models`, copy exact display string |
| `Failed to read cli settings` (warning) | `settings.json` absent | Expected; defaults are used. Create one to customize |
| `Failed to poll FetchAvailableModels` | Network or auth | Check connectivity; check `~/.gemini/config/config.json` |
| `Last check was less than 15 minutes ago` | Auto-updater cooldown | Normal; the updater polls every 15m |

## Workflow F — auth recovery on a fresh machine

Use when: `agy` works (`--version` returns) but every call fails with
auth errors.

```bash
# 1. Confirm the failure shape
LOG=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
grep "not logged into" "$LOG" | head -3

# 2. Trigger browser OAuth
agy -i
# (browser opens, sign in with the Google account that has AI Pro,
#  grant access, close the browser tab)
# In the agy TUI: /exit

# 3. Smoke test
agy -p "Reply with: pong" --model gemini-3.5-flash-low --print-timeout 1m
```

**If the browser doesn't open (SSH/headless):** `agy -i` will print an
authorization URL instead. Paste the URL into a local browser, sign in,
copy the auth code, paste it back into the TUI.

**If the logout slash command was run accidentally:** re-run `agy -i` and sign in again.

## Workflow G — switching model tiers mid-session

Use when: an interactive `agy` session needs a different model (e.g.,
escalate from Flash to Pro for a hard sub-task).

Inside the TUI:

```
/model gemini-3.1-pro-high
/model claude-sonnet-4-6
/model gpt-oss-120b-medium
```

The change applies to the current session only; persistent model
preferences belong in `~/.gemini/config/config.json`.

**Cost reminder:** only the Gemini tiers are subscription-free. Flipping
to Claude mid-session starts a metered bill.

## Workflow H — settings.json without breaking defaults

Use when: persistent settings are needed (default permission mode,
sandbox, trusted workspaces).

```bash
SETTINGS=~/.gemini/antigravity-cli/settings.json

# Back up first (never edit without a timestamped .bak)
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d_%H%M%S)"

# Write a minimal settings.json
cat > "$SETTINGS" <<'EOF'
{
  "enableTerminalSandbox": true,
  "allowNonWorkspaceAccess": false,
  "permissions": {
    "allow": ["read_file", "list_directory", "grep_files", "web_search"]
  },
  "trustedWorkspaces": ["~/projects/myapp"]
}
EOF

# Verify it parses (agy tolerates malformed JSON with warnings)
python3 -m json.tool "$SETTINGS" > /dev/null && echo "OK" || echo "INVALID"
```

**Reload:** settings are read on each `agy` launch — no explicit reload
needed. For a running session, restart `agy`.

**Don't confuse** with `~/.gemini/config/config.json` (shared config,
permissions source when `settings.json` is absent).

## Workflow I — image generation with quota awareness

`agy` can generate images via `agy -p "<prompt>" --model gemini-3.5-flash-low`,
but image gen runs on `gemini-3.1-flash-image` under the hood regardless of
the `--model` you pick, and that model has a **per-model quota** on the
Google AI Pro consumer tier (~10-12 calls per ~5h window). See
`topology.md` → **Quota exhaustion** for the full surface.

### Before a bulk run — check if quota is live

```bash
# Is there a pending QUOTA_EXHAUSTED? Parse the reset timestamp.
LATEST=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
grep -o '"quotaResetTimeStamp"[^,]*' "$LATEST" 2>/dev/null
# If the timestamp is in the future, wait. If absent, quota is live.
```

### Throttled batch (the safe pattern)

```bash
# Max ~10 image calls per ~5h window. sleep 30 between calls.
for slug in bandeja-paisa sushi-rolls hamburguesa-clasica; do
  for variant in 1 2; do
    agy -p "Professional food photography of ${slug}, studio lighting, \
      1024x1024, on a white plate" \
      --model gemini-3.5-flash-low --print-timeout 120s \
      > /tmp/ag-productos/logs/${slug}_${variant}.log 2>&1
    # agy writes the image to ~/.gemini/antigravity-cli/brain/<uuid>/ —
    # parse the path from the log and copy to your output dir.
    sleep 30  # throttle to avoid bursting the hidden IPM cap
  done
done
```

### When you hit 429 — don't retry, choose (with the user)

`QUOTA_EXHAUSTED` is non-transient for agy; retrying with a different
`--model` won't help (same underlying image model). Don't block the user
without options — present the choice and let them pick:

1. Parse `quotaResetTimeStamp` from the log (see **before a bulk run**
   above) and tell the user when the free quota resets (~5h).
2. **Offer the OpenRouter fallback (same model, pay-per-use).**
   `google/gemini-3.1-flash-image` on OpenRouter = ~$0.50/M in,
   $3.00/M out — the exact model agy uses, no subscription cap. Estimate
   the cost for the remaining images and **ask for explicit approval before
   switching** (OR billing is separate from AI Pro; never switch silently).
   Cheaper sibling `google/gemini-2.5-flash-image` (~$0.30/$2.50) also works.
3. On approval, run the remaining batch via the host harness's OpenRouter
   routing (or direct OR calls) instead of `agy -p`, with the same prompts.
4. On decline, either wait for `quotaResetTimeStamp` + 60s then resume with
   `sleep 30`, or use stock photos / Gemini API direct as a last resort.

**Never silently switch to a paid path.** The free AI Pro quota is the
reason agy is the default; falling to OR changes billing and must be a
conscious user choice, not an agent default.

### Image output location

`agy -p` writes generated images to `~/.gemini/antigravity-cli/brain/<uuid>/`.
The response text (or `--output-format json` envelope) references the path.
Copy from there to your project's image dir. Verify the file is a valid
JPEG/PNG > 50KB before committing — a truncated 429 response can leave a
partial or missing file.

**Cap your expectations:** ~10 images per 5h window on AI Pro. For
larger batches, either split across multiple windows (with scheduled
retry) or use a pay-per-use path.
