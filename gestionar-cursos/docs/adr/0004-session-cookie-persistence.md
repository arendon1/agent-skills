# ADR 0004: Session Cookie Persistence with TTL

## Status

Accepted

## Context

After manual login via Chrome, cookies must be transferred to `requests.Session` for scraping. The user wants persistent sessions to avoid re-login on every run.

## Decision

Persist session cookies to disk as JSON (`.moodle_session.json`) with a 7-day TTL.

- **Format**: `{"cookies": [...], "expires_at": "ISO-8601"}`
- **Location**: Same directory as `.browserdata/` (workspace root)
- **TTL**: 7 days from creation
- **Behavior on load**:
  - If file exists and `expires_at` > now: load cookies into `requests.Session`
  - If expired or missing: trigger Chrome login flow

## Rationale

- Cookie file is local to user's machine (low risk)
- 7-day TTL balances convenience with security
- JSON format is human-readable for debugging
- File is gitignored (`.browserdata/` and `.moodle_session.json`)

## Consequences

- **Positive**: Most runs are instant — no browser needed after first login
- **Negative**: Cookie file on disk is a minor security concern
- **Mitigation**: File is in user's workspace, gitignored, has TTL

## Related

- See `browser_api.py` for cookie export/import logic
- See `navegador_cdp.py` for Chrome cookie extraction
