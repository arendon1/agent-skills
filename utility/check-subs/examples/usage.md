# Usage Examples

## First-time setup

```bash
# 1. Create the config file with the keys you have
mkdir -p ~/.config/check-subs
cat > ~/.config/check-subs/config.json <<'EOF'
{
  "openrouter": { "apiKey": "sk-or-v1-..." },
  "minimax":    { "apiKey": "sk-cp-..." }
}
EOF

# 2. (Optional) Add OG cookie if you have an OG subscription
# Edit the config to add:
#   "opencode-go": { "workspaceId": "...", "authCookie": "..." }

# 3. (Optional) Install `agy` if you have Google AI Pro

# 4. Verify config is resolved
check-subs config

# 5. Run a probe
check-subs probe

# 6. See results
check-subs status --human
```

## Routine usage

```bash
# Probe all 4 providers (writes state file)
check-subs probe

# Probe just one
check-subs probe openrouter
check-subs probe minimax
check-subs probe agy

# Read the latest state without re-probing
check-subs status
check-subs status --human
```

## Post-dispatch feedback

When a real dispatch hits a rate limit, record the reset so the next probe
doesn't waste cycles:

```bash
# OG: rollingUsage window is now at 100%, resets in 14523 seconds
check-subs record opencode-go 5h 100 14523

# Minimax: weekly window exhausted
check-subs record minimax weekly 100 518400

# AGY: 5h window exhausted (v1: only liveness available, so use a heuristic)
# AGY doesn't return reset time, so the dispatcher should pick a reasonable default
check-subs record agy 5h 100 18000  # 5h default
```

## Integration with a dispatcher

The dispatcher script (e.g. a wrapper around the user's preferred model
router) should:

```bash
# 1. Before dispatching, check if the target is alive
state=$(jq -r ".providers.${target}.status" ~/.local/state/check-subs/state.json)
if [ "$state" != "ok" ]; then
  echo "target $target is $state, falling back to OR" >&2
  target=openrouter
fi

# 2. Dispatch to $target (omitted)

# 3. After dispatch, if 429/2056/Resource-exhausted, record the reset
if got_rate_limit; then
  check-subs record "$target" "$window" 100 "$reset_seconds"
fi
```

## In a loop / cron

If the user wants periodic probing (not strictly required — `check-subs`
runs on demand and the dispatcher updates state after 429s), they can wire
it into a `launchd` plist or a simple loop:

```bash
# Refresh all 4 every 5 minutes, forever
while true; do
  check-subs probe >/dev/null 2>&1
  sleep 300
done
```

But for most users, on-demand + post-dispatch feedback is enough.

## State file consumption

Any other process can read the state without invoking `check-subs`:

```bash
# What's the next probe time for OG?
jq -r '.providers.opencode-go.next_probe_at' ~/.local/state/check-subs/state.json

# Is AGY alive right now?
jq -r '.providers.agy.liveness.alive // false' ~/.local/state/check-subs/state.json

# What windows are exhausted?
jq -r '.providers | to_entries[] | select(.value.status == "ok") | .key as $p |
       .value.windows | to_entries[] | select(.value.consumedPercent >= 90) |
       "\($p)/\(.key): \(.value.consumedPercent)%"' \
       ~/.local/state/check-subs/state.json
```
