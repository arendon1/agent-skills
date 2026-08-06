# LESSONS — use-mineru-cloud build

Invariants learned building + live-testing this skill. Worth auditing again if
behavior drifts.

## Skill / API invariants

1. **Python SDK attrs are snake_case, JS camelCase.** `result.content_list`
   (not `contentList`), `result.err_code`, `extract_progress` → `progress`.
   Mixing conventions raises AttributeError at the worst moment.
2. **`submit()` returns a batch id even for a single file.** `get_task()` only
   works for ids obtained elsewhere. Manual polling must use `get_batch()`.
3. **Auth-check without quota cost:** `get_batch()` with a bogus UUID →
   `AuthError` = bad token, `TaskNotFoundError` = valid. Never submit a real
   file just to test auth.
4. **Foreign URLs (github/aws) time out on the MinerU side** (Chinese service).
   For such files: download locally → convert local path (presigned upload).
   This is the skill's default path anyway.
5. **Precision limits: 200MB / 200 pages** (docs), flash 10MB / 20 pages.
   Rate policy: 50 files/min submit, 5,000/day (100 HTML), 1,000 req/min poll.
6. **`Authorization: Bearer <token>` only.** AK/SK pairs are NOT supported by
   the v4 API (401 A0202) — don't try to build an HMAC signer.

## Tooling invariants (this repo)

7. **ClickUp v2 `PUT /task/{id}` with `list_id` silently does NOT move tasks.**
   Recreate in the target list, or the task stays put while status changes.
8. **ClickUp create-task response is FLAT JSON** (`id` at top level), not
   wrapped in `task`. Parsing `resp["task"]["id"]` yields None; guard for both.
9. **`.env` must be gitignored** — `client.py` reads `.env` first, and this
   repo is public. Root `.gitignore` now covers `.env`, `**/.env`, `.env.*`.
10. **Termux deployment is manual tar-over-ssh** (no rsync on the phone).
    `~/.pi/agent/skills/<skill>` → symlink to `~/.agents/skills/<skill>`.
    The phone's `.skill-lock.json` tracks only synced sources — manual deploys
    live outside it (discovery still works via the symlink).
11. **Phone Python is 3.14** — local `mineru` pip requires `<3.14`, so the
    cloud-only split is enforced by the toolchain, not just preference.
