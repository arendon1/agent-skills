# Risk thresholds — when the agent pauses without being asked

The agent defaults to autonomous. It pauses on its own ONLY when the
change crosses a risk threshold. The thresholds are heuristic, not
absolute — the goal is to catch the cases the operator would obviously
want to review, not to be exhaustive.

## Default thresholds (v1)

Pause automatically when ANY of these is true after a unit of work:

| Signal | Threshold | Rationale |
|---|---|---|
| lines changed | `>= 80` (sum of `+` and `-`) | a change this size usually has a story; let the operator see it |
| files changed | `>= 4` | multi-file changes touch more than the agent can self-verify in a single head |
| sensitive paths | any match in `auth`, `security`, `secret`, `credentials`, `token`, `password`, `schema`, `migration`, `migrate`, `lock`, `lockfile`, `ci`, `.github`, `deploy`, `release`, `Dockerfile`, `compose`, `terraform` | these have higher blast radius and harder rollback |
| new dependency | any new entry in `package.json` / `requirements.txt` / `pyproject.toml` / `go.mod` / `Cargo.toml` / `pubspec.yaml` | supply-chain and lockfile cascades |
| revert | `git revert`, `git reset`, manual undo of a recent commit, or any change whose intent is "undo X" | reverts deserve human eyes |
| low confidence | the agent self-reports uncertainty on the change (e.g. couldn't find a clear pattern to follow, had to invent a heuristic, multiple plausible approaches) | self-reported risk is a real signal |
| config changes | changes to `.env*`, `*.config.*`, `tsconfig.*`, `pyproject.toml` tool sections, CI workflow files, git hooks | config drift is hard to roll back cleanly |
| new public API | introduces or removes a public function, class, type, route, or CLI flag | API surface decisions deserve a review |

Any single signal fires the pause. The agent reports WHICH signal(s)
fired in the preamble.

## Reading the thresholds at runtime

```bash
# defaults
THRESHOLD_LINES=80
THRESHOLD_FILES=4
THRESHOLD_SENSITIVE='auth|security|secret|credentials|token|password|schema|migration|migrate|lock|lockfile|ci|\.github|deploy|release|Dockerfile|compose|terraform'
THRESHOLD_DEPS='package\.json|requirements\.txt|pyproject\.toml|go\.mod|Cargo\.toml|pubspec\.yaml'
```

`git diff --stat` is the cheap pre-check:

```text
 src/auth.ts        |  24 +++++----
 test/auth.test.ts  |  12 +++--
 2 files changed, 36 insertions(+)
```

2 files / 36 lines / one of the paths matches `auth` → pause. The agent
states the reason in the preamble: "Pausé porque: paths en `auth/*`."

## Override per request

The operator can override the auto-pause for a specific request with
the word `auto`:

> "Refactor auth, but `auto` for this one."

The agent acknowledges in the preamble: "Procedo sin pausa (auto
override)." It still prints the preamble (so the operator has a
record) but does not pause for confirmation. Override is per-request,
not per-session.

The operator can also override with `skip-review`, `no-review`,
`autonomo`, `autónomo`, `without review`, `sin revisión`, `sin
revisar`. All map to the same override.

## Override per session

A persistent override is possible via the config file:

```toml
# ~/.config/agent-skills/use-hunk.toml
[thresholds]
lines = 200            # raise the line threshold
files = 8              # raise the file threshold
sensitive_paths = []   # disable path-based auto-pause
auto_pause = false     # disable risk-aware auto-pause entirely
```

When `auto_pause = false`, only operator keywords trigger a pause. Use
this when the operator wants the full original (keyword-only) behavior.

## Operator can lower thresholds too

The operator may want MORE pauses, not fewer. Configuration:

```toml
[thresholds]
lines = 30             # pause on anything > 30 lines
files = 2              # pause on any multi-file change
sensitive_paths = ["*"]  # pause on EVERY path (back to keyword+path)
```

Valid for code-review-heavy work, junior collaborators, or high-stakes
repos. The skill reads the config file before every pause decision;
changes take effect on the next unit of work.

## Examples — what fires the pause

| Change | Auto-pause? | Why |
|---|---|---|
| One-line typo fix in `src/utils/string.ts` | no | 1 line, 1 file, no sensitive path |
| Rename a private helper across 3 files | no | under thresholds |
| Add a new route in `src/api/users.ts` | yes | new public API |
| Update `package.json` to add a dep | yes | new dependency |
| Edit `src/auth/session.ts` (any size) | yes | `auth/*` sensitive path |
| Refactor 5 files, 120 lines, all in `src/ui/` | yes | over both line and file thresholds |
| Add a test, no production code change | no | under thresholds, no sensitive paths |
| `git revert HEAD~1` then small adjustment | yes | revert + sensitive path likely |
| Edit `Dockerfile` | yes | `Dockerfile` matches sensitive path |
| Edit `.github/workflows/ci.yml` | yes | `.github` matches |
| Bump `package-lock.json` only (no source change) | no | lockfile-only is mechanical; the lockfile match is overridden by "no source code changed" |
| Edit a markdown doc | no | not in the path list; under thresholds by default |

## When the threshold fires but the change is obviously trivial

The agent MUST still pause, but the preamble is short:

```text
Listo. 1 archivo, 1 línea. (Pausé porque: path en `auth/*`.)
Cambié src/auth/session.ts:42 — typo fix.
```

Two lines is enough. The pause is for the operator's audit trail, not
to gatekeep trivial work. The operator types `go` and the agent
proceeds — total friction: ~3 seconds.

## Config discovery

The skill reads `~/.config/agent-skills/use-hunk.toml` at the start of
each pause decision. If the file is missing, all defaults apply. If
the file has parse errors, the agent falls back to defaults and prints
a one-time warning: "Config parse error in use-hunk.toml — using
defaults."
