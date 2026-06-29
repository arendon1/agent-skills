---
name: caveman
description: |
  Compressed English encoding for plan artifacts and spec-adjacent prose.
  Cuts tokens ~75% vs prose while staying readable. Applies to PRD.md, ARD.md,
  SPEC.md, PLAN.md, LESSONS.md, RESEARCH.md, CONTEXT.md.
  Use when writing to a plan artifact, spec-adjacent prose, or when the user says
  "caveman", "compress this", "be brief", "write to PLAN.md".
invocation: auto
layer: utility
metadata:
  version: "1.0.0"
---

# caveman — spec-adjacent compression

Compressed English for plan artifacts. Saves tokens (loaded every invocation)
and reads fast for both agent and human. Symbols unambiguous; grammar lean.

## WHEN (self-trigger)

- Writing to a plan artifact: `PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`,
  `LESSONS.md`, `RESEARCH.md`, `CONTEXT.md`.
- Writing spec-adjacent prose (invariants, bug rows, task rows, interface shapes).
- User says "caveman", "compress this", "be brief".

## SCOPE

**Apply caveman to:** plan artifacts (listed above) + spec-adjacent prose.

**Do NOT apply caveman to:**
- Code (source files).
- Commit messages, PR descriptions, release notes.
- Diff comments in code.
- External-facing docs (RFC, pitch, customer-facing).
- User-facing explanations when the user asks for prose.
- Chat to the human in the terminal/shell (normal English; emoji allowed there
  for status/severity per the traffic-light palette below).

Caveman is compression, not amputation. If cutting a word loses a fact, keep it.

---

## TOOLKIT

Apply in priority order. Grammar is the biggest token win. Symbols add density.
Use words for anything obscure. 7 layers.

### 1. Grammar

- Drop articles (`a`, `an`, `the`).
- Drop filler (`just`, `really`, `basically`, `simply`, `actually`).
- Drop auxiliary verbs where fragments work (`is`, `are`, `was`, `were`, `being`).
- Drop hedging (`might`, `perhaps`, `could be worth`).
- Drop pleasantries.
- Use short synonyms: `fix` > `implement`, `run` > `execute`, `big` > `extensive`.
- Fragments are fine.

### 2. Programming operators (ligature-clean)

Prefer over words. ASCII so they survive in any artifact or commit.

| Symbol | Means | Example |
|---|---|---|
| `->` | leads to / becomes / triggers | `auth timeout -> 401` |
| `<-` | comes from / derived from | `price <- catalog.base * qty` |
| `=>` | implies / therefore / returns | `token expired => reject` |
| `>=` | at least | `retry count >= 3` |
| `<=` | at most | `batch size <= 100` |
| `>` `<` | more than / less than | `latency > 200ms` |
| `!=` | differs from / not | `status != done` |
| `==` | equals exactly | `role == admin` |
| `~` | approximately | `~95% of requests` |
| `&&` | and | `auth && verified` |
| `\|\|` | or | `admin \|\| owner` |
| `!` | not | `!cached` |
| `in` | member of | `user in admins` |
| `not in` | not member of | `guest not in allowed` |
| `:=` | defined as | `deadline := now + 24h` |

### 3. RFC 2119 keywords (modality)

Use for requirement strength. These words are load-bearing — never compress them away.

| Keyword | Means | Example |
|---|---|---|
| `MUST` | required, non-negotiable | `MUST check expiry before handler` |
| `MUST NOT` / `NEVER` | forbidden | `NEVER log raw tokens` |
| `SHOULD` | recommended | `SHOULD retry with backoff` |
| `MAY` / `?` | optional | `MAY cache result?` |

### 4. Ranges & structure

| Symbol | Means | Example |
|---|---|---|
| `1..*` | one or more | `user 1..* orders` |
| `0..1` | zero or one | `order 0..1 coupon` |
| `n..m` | range | `2..5 retries` |
| `§` | section reference | `see §V.2` |

Addressing: `§<S>.<n>` = section.item. `§V.2` = invariants section, item 2.
Commits, PRs, and chat all reference by §. Zero ambiguity.

### 5. Type (conventional-commit words)

Type is always a conventional-commit word — never an emoji. Works in artifacts,
commits, and chat.

| Word | Means | Example |
|---|---|---|
| `feat` | new feature | `feat: POST /x -> 200 {id}` |
| `fix` | bug fix | `fix: B1 token < not <=` |
| `refactor` | no behavior change | `refactor: extract validation mw` |
| `test` | test-only | `test: TestV7_Idempotent` |
| `docs` | documentation | `docs: update §V` |
| `chore` | tooling / deps / cleanup | `chore: bump deps` |
| `perf` | performance | `perf: cache auth check` |
| `ci` | CI / CD | `ci: add deploy job` |

---

## EMOJI — CHAT ONLY, NEVER IN ARTIFACTS

Emoji unicode is garbage in persisted artifacts (`.md`, code, commits, shell
output). Artifacts use ASCII words. Chat to the human in the terminal/shell MAY
use the fixed palette below for status/severity scanning.

### 6. Semantic emoji (chat-only, traffic-light palette)

Three circles for severity, one glyph for in-progress. Nothing else.

| Chat emoji | Artifact ASCII | Means |
|---|---|---|
| 🟢 | `PASS` / `OK` / `✓` | done / holds / ok |
| 🟡 | `WARN` / `HARDEN` | warning / should fix |
| 🔴 | `FAIL` / `BLOCK` / `✗` / `NEVER` | failed / critical / forbidden |
| 🔵 | `INFO` | note / informational |
| 🚧 | `WIP` | in progress |

**Forbidden (too many variants):** 🟠 🟣 ⚫️ ⚪️ 🟤 and all square variants
🟥 🟧 🟨 🟩 🟦 🟪 ⬛️ ⬜️ 🟫. Also drop ✅ ❌ ⚠️ 🛑 from chat — redundant with the
traffic-light circles. Keep `✓` / `✗` as artifact ASCII chars.

### 7. Directional emoji (chat-only, magnitude & trend)

Express change and trend — distinct from `->` / `=>` which express logical flow.
Chat-only; artifacts use ASCII.

| Chat emoji | Artifact ASCII | Means | Example |
|---|---|---|---|
| ⬆️ | `+` / `up` | increase / upgrade | `⬆️ retry to 5` |
| ⬇️ | `-` / `down` | decrease / downgrade | `⬇️ batch to 50` |
| ↗️ | `up` trend | trend up (gradual) | `↗️ p95 latency` |
| ↘️ | `down` trend | trend down (gradual) | `↘️ error rate` |
| ↔️ | `<->` | bidirectional / two-way | `↔️ sync both ways` |

**Reserved for navigation/sort only** (sparingly, context-dependent):
◀️ ▶️ previous/next, 🔼 🔽 priority/sort up/down. **Avoid** ↖️ ↙️ ↕️ — too niche,
use words.

---

## TODO CHECKBOX (task lists only)

`[x]` / `[ ]` are reserved for task lists (complete/incomplete items). Never use
them as general pass/fail status. Example — a `PLAN.md` task table:

```
id|status|task|cites
T1|[x]|scaffold repo|-
T2|[ ]|impl §I.api POST /x|V2
T3|[ ]|add §V.1 middleware|V1,I.api
```

For in-progress, mark `[ ]` and add a `WIP` flag in an adjacent cell, or use `~`.
Status values: `[x]` done, `[ ]` todo, `~` wip.

---

## DROPPED (obscure math)

Dropped from earlier cavekit drafts. Use plain words instead — clearer for a
non-always-technical reader.

| Dropped | Use instead |
|---|---|
| `∀` | `every` |
| `∃` | `exists` |
| `∴` | `so` / `=>` |
| `⊥` | `never` / `NEVER` |
| `∈` | `in` |
| `∉` | `not in` |
| `≤` | `<=` |
| `≥` | `>=` |
| `≠` | `!=` |

If a word is clearer than a symbol, use the word.

---

## PRESERVE VERBATIM

Never compress:

- Code blocks, snippets, one-liners with backticks.
- Paths: `src/auth/mw.go`.
- URLs.
- Identifiers: function names, variable names, env vars.
- Numbers and versions.
- Error message strings.
- SQL, regex, JSON, YAML.
- Quoted strings.

---

## ARTIFACT vs CHAT — quick reference

| Surface | Encoding | Emoji? |
|---|---|---|
| `PRD.md` / `ARD.md` / `SPEC.md` / `PLAN.md` / `LESSONS.md` / `RESEARCH.md` / `CONTEXT.md` | caveman | never — ASCII words |
| Code | normal (language rules) | never |
| Commit message / PR description / release notes | normal English | never |
| Diff comment in code | normal English | never |
| External-facing doc (RFC, pitch, customer) | normal English | never |
| Chat to the human in terminal/shell | normal English | yes — traffic-light + directional palette |
| Shell command output | normal | never |

---

## BOUNDARIES

- User asks for a prose explanation → switch to normal English.
- Commit messages, PR descriptions → normal English.
- Diff comments in code → normal English.
- External-facing docs (RFC, pitch) → normal English.
- Artifacts (`.md` files, code, shell output) → no emoji; use ASCII equivalents.
- Chat to the human in terminal/shell → emoji OK for status/severity scanning.

---

## SHAPES (toned — no math symbols)

**Invariant** (`§V`):
```
V<n>: <subject> <relation> <condition>
V1: MUST auth check every req before handler
V2: token expiry <= current_time => reject
V3: DB write MUST be in transaction
```

**Bug row** (pipe table under `§B`, owned by `lessons`):
```
id|date|cause|fix
B1|2026-04-20|token `<` not `<=`|V2
```

**Task row** (pipe table under `§T`, owned by `plan`; `build` flips status only):
```
id|status|task|cites
T1|[x]|scaffold repo|-
T2|[ ]|impl §I.api POST /x|V2
T3|~|add §V.1 middleware|V1,I.api
```
Status: `[x]` done, `~` wip, `[ ]` todo. Escape literal `|` as `\|`. Empty = `-`.

**Interface** (`§I`):
```
<kind>: <name> -> <shape>
api: POST /x -> 200 {id:string}
cmd: `foo bar <arg>` -> stdout JSON
env: FOO_KEY MUST be set
```

---

## EXAMPLES

**Bad (prose):**
> The authentication middleware must verify the token expiry on every request before allowing the handler to execute, and it must never log raw tokens.

**Good (caveman):**
> `V1: MUST check token expiry before handler && NEVER log raw tokens`

---

**Bad (prose):**
> We discovered that the token expiration check was using strict less-than, causing tokens to be rejected exactly at expiry.

**Good (caveman):**
> `fix B1: token < not <= => reject @ expiry boundary`

---

**Bad (prose):**
> Invariant 2 is violated at mw.go line 47; this is a critical bug and must be fixed before build.

**Good (caveman):**
> `FAIL V2 violated: mw.go:47. BLOCK B1. MUST fix before build.`

---

**Bad (prose):**
> A user has one or more orders, and an order may have zero or one coupon applied.

**Good (caveman):**
> `user 1..* orders; order 0..1 coupon?`

---

**Bad (chat with emoji in artifact):**
> `## Status: ✅ all green, ⚠️ 1 warn`

**Good (artifact ASCII):**
> `## Status: PASS all green, WARN 1`

**Good (chat to human):**
> 🟢 all green, 🟡 1 warn

---

## WHY CAVEMAN FOR ARTIFACTS

Artifacts are loaded every invocation. ~75% fewer tokens = ~75% fewer dollars and
faster reads. Human skims fast too. Symbols are unambiguous across agent and
reader. Math symbols were dropped because a non-always-technical reader stumbles on
`∀`/`⊥`; `every`/`NEVER` carry the same force with no learning curve.

## WHEN UNSURE

If cutting a word loses a fact, keep it. Caveman is compression, not amputation.
When the user asks for an explanation, switch to normal English. When the surface
is a commit, PR, code comment, or external doc, use normal English.
